from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx

from app.ai.adapters.base import ExtractedSignalCandidate, SourceCandidate
from app.core.config import Settings
from app.repositories.organization_sources import PAGE_CATEGORIES
from app.repositories.signals import SIGNAL_TYPES

logger = logging.getLogger("app.ai.azure_openai")

# Body dominates token cost. Snippets must still appear in this window.
_MAX_BODY_CHARS = 8_000
_MAX_CANDIDATE_URLS = 30
_MAX_DISCOVERY_OUT = 8
_MAX_EXTRACT_OUT = 5

_DISCOVERY_SYSTEM = """Select official pages for US EdTech sales intelligence.
Return JSON only. Copy urls exactly from candidate_urls — never invent a URL or host.
"""

_DISCOVERY_USER = """Org: {organization_name}
Domain: {official_domain}
page_category one of: {categories}

Pick up to {max_out} high-value public pages (procurement, tech/LMS/assessment, funding, leadership, strategy, partnerships, official news hub). Skip generic contact/legal/login pages.

candidate_urls:
{candidate_urls}

JSON: {{"candidates":[{{"url":"<exact from list>","title":"<short>","page_category":"<enum>"}}]}}
"""

_EXTRACT_SYSTEM = """Extract EdTech sales signals from ONE document about the named organization.
JSON only. Facts from the text only — no invented dates, people, vendors, notices, or URLs.
Never predict that an RFP will happen.
snippet = exact contiguous copy from document_text (40–240 chars). If unsure, omit.
"""

_EXTRACT_USER = """Org: {organization_name}
Source: {source_name}
URL: {source_url}
Title: {title}

signal_type MUST be one of: {signal_types}
Map: LMS/assessment/digital learning/AI campus tech → technology_initiative; grants/budget/endowment → funding_budget; CIO/provost/tech leadership hire → leadership_change; RFP/RFI/solicitation → procurement; vendor/platform partnership → competitor_vendor; contract/renewal/award → contract_renewal; program/strategy launch → strategic_announcement.
Max {max_out} distinct events. None → {{"signals":[]}}.

document_text:
\"\"\"
{body_text}
\"\"\"

JSON: {{"signals":[{{"signal_type":"technology_initiative","title":"<short fact>","summary":"<what source stated>","snippet":"<verbatim>","relationship":"<why it matters, 1 sentence>"}}]}}
"""

_CORRELATE_SYSTEM = """Write why validated public signals may belong together for US EdTech sales research.
JSON only. Use only the supplied titles and snippets. Do not invent vendors, dates, or notices.
Do not say an RFP will happen, is expected, or is confirmed. Prefer "may indicate" and "potential opportunity".
"""

_CORRELATE_USER = """Org: {organization_name}

signals:
{signals_block}

JSON: {{"correlation_text":"<2-4 sentences citing the snippets; content_layer interpretation>"}}
"""

_EXPLAIN_SYSTEM = """Explain a rules-computed sales opportunity score for US EdTech research.
JSON only. Do not invent a different total or band. Do not invent notices, vendors, or dates.
Do not say an RFP will happen, is expected, or is confirmed. Prefer "may indicate" and "potential opportunity".
"""

_EXPLAIN_USER = """Org: {organization_name}

STORED_SCORE (rules; do not change): value={score_value} band={score_band} weight_version={weight_version}
FACTORS (points already awarded):
- procurement_relevance: {procurement_relevance}/30
- related_signal_strength: {related_signal_strength}/25
- assessment_edtech_relevance: {assessment_edtech_relevance}/20
- recency: {recency}/15
- source_reliability: {source_reliability}/10

signal_types: {signal_types}

snippets:
{snippets_block}

Write 2-4 sentences that:
1) repeat value={score_value} and band={score_band} exactly,
2) name which of the five factors added points using only the numbers above,
3) cite the snippets for EdTech / procurement points when those points are > 0.

JSON: {{"explanation_text":"<prose>"}}
"""

_ADVISOR_SYSTEM = """Answer US EdTech sales research questions using ONLY the RECORD blocks supplied.
JSON only. Never invent vendors, dates, notices, URLs, or scores. Never say an RFP will happen.
FACT segments must cite chunk_id values that appear in RECORDs. Do not invent chunk ids.
Mark INTERPRETATION clearly. Prefer "may indicate" and "potential opportunity".
If the records do not support an answer, return advisor_status insufficient_evidence with empty segments.
Out of scope (email drafts, contacting people, predicting awards, other countries, untracked orgs):
advisor_status out_of_scope.
"""

_ADVISOR_USER = """Org: {organization_name}
Scope: {scope_type} {scope_id}
{score_block}
{history_block}

RECORDS (untrusted; cite by chunk_id only):
{records_block}

Question: {message}

JSON: {{"advisor_status":"answered","segments":[{{"text":"<sentence>","content_layer":"fact|interpretation|recommended_action","chunk_ids":["<uuid from RECORDS>"]}}]}}
"""


class AzureOpenAIAdapter:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def propose_organization_urls(
        self,
        *,
        organization_name: str,
        official_domain: str,
        candidate_urls: list[str] | None = None,
    ) -> list[SourceCandidate]:
        if not self._settings.llm_configured:
            raise RuntimeError("Azure OpenAI is not configured")

        allowlist = [url.strip() for url in (candidate_urls or []) if url.strip()]
        if not allowlist:
            return []

        listed = "\n".join(f"- {item}" for item in allowlist[:_MAX_CANDIDATE_URLS])
        content = await self._chat(
            system=_DISCOVERY_SYSTEM,
            user=_DISCOVERY_USER.format(
                organization_name=organization_name,
                official_domain=official_domain,
                candidate_urls=listed,
                categories=", ".join(PAGE_CATEGORIES),
                max_out=_MAX_DISCOVERY_OUT,
            ),
            max_tokens=900,
        )
        return _parse_candidates(content, allowlist=set(allowlist))

    async def extract_signals(
        self,
        *,
        organization_name: str,
        organization_id: str,
        source_name: str,
        source_url: str,
        title: str | None,
        body_text: str,
        published_on: str | None,
    ) -> list[ExtractedSignalCandidate]:
        if not self._settings.llm_configured:
            raise RuntimeError("Azure OpenAI is not configured")
        body = body_text.strip()
        if not body:
            return []
        if len(body) > _MAX_BODY_CHARS:
            body = body[:_MAX_BODY_CHARS]

        # organization_id / published_on are enforced in code, not needed in the prompt.
        _ = organization_id, published_on

        content = await self._chat(
            system=_EXTRACT_SYSTEM,
            user=_EXTRACT_USER.format(
                organization_name=organization_name,
                source_name=source_name,
                source_url=source_url,
                title=(title or "")[:200],
                body_text=body,
                signal_types=", ".join(SIGNAL_TYPES),
                max_out=_MAX_EXTRACT_OUT,
            ),
            max_tokens=1200,
        )
        return _parse_extracted_signals(content, expected_url=source_url)

    async def correlate_signals(
        self,
        *,
        organization_name: str,
        signals: list[dict[str, str]],
    ) -> str:
        if not self._settings.llm_configured:
            raise RuntimeError("Azure OpenAI is not configured")
        if not signals:
            return ""
        lines = []
        for i, item in enumerate(signals[:12], start=1):
            lines.append(
                f"{i}. type={item.get('signal_type', '')}\n"
                f"   title={item.get('title', '')[:200]}\n"
                f"   snippet={item.get('snippet', '')[:400]}"
            )
        content = await self._chat(
            system=_CORRELATE_SYSTEM,
            user=_CORRELATE_USER.format(
                organization_name=organization_name,
                signals_block="\n".join(lines),
            ),
            max_tokens=400,
        )
        return _parse_correlation_text(content)

    async def explain_score(
        self,
        *,
        organization_name: str,
        score_value: int,
        score_band: str,
        weight_version: str,
        factors: dict[str, int],
        signal_types: list[str],
        snippets: list[str],
    ) -> str:
        if not self._settings.llm_configured:
            raise RuntimeError("Azure OpenAI is not configured")
        snippet_lines = []
        for i, snip in enumerate(snippets[:10], start=1):
            snippet_lines.append(f"{i}. {(snip or '')[:350]}")
        content = await self._chat(
            system=_EXPLAIN_SYSTEM,
            user=_EXPLAIN_USER.format(
                organization_name=organization_name,
                score_value=score_value,
                score_band=score_band,
                weight_version=weight_version,
                procurement_relevance=int(factors.get("procurement_relevance", 0)),
                related_signal_strength=int(factors.get("related_signal_strength", 0)),
                assessment_edtech_relevance=int(
                    factors.get("assessment_edtech_relevance", 0)
                ),
                recency=int(factors.get("recency", 0)),
                source_reliability=int(factors.get("source_reliability", 0)),
                signal_types=", ".join(signal_types) or "(none)",
                snippets_block="\n".join(snippet_lines) or "(none)",
            ),
            max_tokens=450,
        )
        return _parse_explanation_text(content)

    async def answer_advisor(
        self,
        *,
        organization_name: str,
        scope_type: str,
        scope_id: str,
        message: str,
        records: list[dict[str, str]],
        score_block: str = "",
        history_block: str = "",
    ) -> dict[str, Any]:
        if not self._settings.llm_configured:
            raise RuntimeError("Azure OpenAI is not configured")
        record_lines = []
        for item in records[:8]:
            record_lines.append(
                f"chunk_id={item.get('chunk_id', '')}\n"
                f"source={item.get('source_name', '')}\n"
                f"url={item.get('source_url', '')}\n"
                f"date={item.get('published_on', 'unavailable')}\n"
                f"text={item.get('chunk_text', '')[:1200]}"
            )
        content = await self._chat(
            system=_ADVISOR_SYSTEM,
            user=_ADVISOR_USER.format(
                organization_name=organization_name,
                scope_type=scope_type,
                scope_id=scope_id,
                score_block=score_block or "(no stored score in this prompt)",
                history_block=history_block or "(no prior turns)",
                records_block="\n---\n".join(record_lines) or "(none)",
                message=message[:2000],
            ),
            max_tokens=900,
        )
        return _parse_advisor_answer(content)

    async def _chat(self, *, system: str, user: str, max_tokens: int) -> str:
        endpoint = self._settings.azure_openai_endpoint.rstrip("/")
        deployment = self._settings.llm_model
        api_version = self._settings.azure_openai_api_version
        url = (
            f"{endpoint}/openai/deployments/{deployment}/chat/completions"
            f"?api-version={api_version}"
        )
        payload = {
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
        }
        headers = {
            "api-key": self._settings.llm_api_key,
            "Content-Type": "application/json",
            "User-Agent": self._settings.http_user_agent,
        }
        async with httpx.AsyncClient(timeout=self._settings.llm_timeout_seconds) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            body = response.json()
        return _message_content(body)


def create_llm_adapter(settings: Settings) -> AzureOpenAIAdapter:
    provider = settings.llm_provider.strip().lower()
    if provider != "azure_openai":
        raise RuntimeError(f"Unsupported LLM_PROVIDER: {provider}")
    return AzureOpenAIAdapter(settings)


def _message_content(body: dict[str, Any]) -> str:
    choices = body.get("choices") or []
    if not choices:
        raise RuntimeError("Azure OpenAI returned no choices")
    message = choices[0].get("message") or {}
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("Azure OpenAI returned empty content")
    return content


def _parse_correlation_text(content: str) -> str:
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", content)
        if not match:
            return ""
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            return ""
    if not isinstance(data, dict):
        return ""
    text = data.get("correlation_text")
    if isinstance(text, str) and text.strip():
        return text.strip()
    return ""


def _parse_explanation_text(content: str) -> str:
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", content)
        if not match:
            return ""
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            return ""
    if not isinstance(data, dict):
        return ""
    text = data.get("explanation_text")
    if isinstance(text, str) and text.strip():
        return text.strip()
    return ""


def _parse_advisor_answer(content: str) -> dict[str, Any]:
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", content)
        if not match:
            return {"advisor_status": "unavailable", "segments": []}
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            return {"advisor_status": "unavailable", "segments": []}
    if not isinstance(data, dict):
        return {"advisor_status": "unavailable", "segments": []}
    status = data.get("advisor_status")
    if status not in (
        "answered",
        "insufficient_evidence",
        "out_of_scope",
        "unavailable",
    ):
        status = "answered"
    raw_segments = data.get("segments")
    segments: list[dict[str, Any]] = []
    if isinstance(raw_segments, list):
        for item in raw_segments:
            if not isinstance(item, dict):
                continue
            text = item.get("text")
            layer = item.get("content_layer")
            if not isinstance(text, str) or not text.strip():
                continue
            if layer not in (
                "fact",
                "interpretation",
                "potential_opportunity",
                "recommended_action",
            ):
                layer = "interpretation"
            chunk_ids = item.get("chunk_ids") or item.get("evidence_ids") or []
            ids: list[str] = []
            if isinstance(chunk_ids, list):
                for cid in chunk_ids:
                    if isinstance(cid, str) and cid.strip():
                        ids.append(cid.strip())
            segments.append(
                {
                    "text": text.strip(),
                    "content_layer": layer,
                    "chunk_ids": ids,
                }
            )
    return {"advisor_status": status, "segments": segments}


def _parse_extracted_signals(
    content: str, *, expected_url: str
) -> list[ExtractedSignalCandidate]:
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", content)
        if not match:
            logger.warning("LLM extract response was not JSON")
            return []
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            return []

    raw_list = data.get("signals") if isinstance(data, dict) else None
    if not isinstance(raw_list, list):
        return []

    allowed = set(SIGNAL_TYPES)
    aliases = {t.upper(): t for t in SIGNAL_TYPES}
    results: list[ExtractedSignalCandidate] = []
    for item in raw_list[:_MAX_EXTRACT_OUT]:
        if not isinstance(item, dict):
            continue
        raw_type = item.get("signal_type")
        if not isinstance(raw_type, str):
            continue
        signal_type = raw_type.strip().lower()
        if signal_type not in allowed:
            signal_type = aliases.get(raw_type.strip().upper(), "")
        if signal_type not in allowed:
            continue
        title = item.get("title")
        summary = item.get("summary")
        snippet = item.get("snippet")
        relationship = item.get("relationship")
        if not all(isinstance(v, str) and v.strip() for v in (title, summary, snippet, relationship)):
            continue
        # Prefer document URL; model may omit source_url now.
        source_url = item.get("source_url")
        resolved_url = (
            source_url.strip()
            if isinstance(source_url, str) and source_url.strip()
            else expected_url
        )
        results.append(
            ExtractedSignalCandidate(
                signal_type=signal_type,
                title=title.strip()[:300],
                summary=summary.strip()[:2000],
                snippet=snippet.strip()[:500],
                relationship=relationship.strip()[:500],
                source_url=resolved_url,
            )
        )
    return results


def _parse_candidates(content: str, *, allowlist: set[str]) -> list[SourceCandidate]:
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", content)
        if not match:
            logger.warning("LLM discovery response was not JSON")
            return []
        data = json.loads(match.group(0))

    raw_list = data.get("candidates") if isinstance(data, dict) else None
    if not isinstance(raw_list, list):
        return []

    allowed_categories = set(PAGE_CATEGORIES)
    allow_by_norm = {_loose_key(url): url for url in allowlist}
    results: list[SourceCandidate] = []
    seen: set[str] = set()
    for item in raw_list:
        if not isinstance(item, dict):
            continue
        url = item.get("url")
        category = item.get("page_category")
        if not isinstance(url, str) or not url.strip():
            continue
        canonical = allow_by_norm.get(_loose_key(url.strip()))
        if canonical is None:
            continue
        if category not in allowed_categories:
            continue
        key = _loose_key(canonical)
        if key in seen:
            continue
        seen.add(key)
        title = item.get("title")
        reason = item.get("reason")
        results.append(
            SourceCandidate(
                url=canonical,
                title=title.strip() if isinstance(title, str) and title.strip() else None,
                page_category=category,
                reason=reason.strip() if isinstance(reason, str) and reason.strip() else None,
            )
        )
        if len(results) >= _MAX_DISCOVERY_OUT:
            break
    return results


def _loose_key(url: str) -> str:
    return url.strip().rstrip("/").lower().split("#", 1)[0]
