from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

import httpx

from app.ai.adapters.base import ExtractedSignalCandidate, SourceCandidate
from app.ai.persona_prompts import PERSONA_SYSTEM, build_persona_user_prompt, parse_persona_answer
from app.core.config import Settings
from app.repositories.organization_sources import PAGE_CATEGORIES
from app.repositories.signals import SIGNAL_TYPES

logger = logging.getLogger("app.ai.azure_openai")

# Body dominates token cost. Snippets must still appear in this window.
_MAX_BODY_CHARS = 8_000
_MAX_CANDIDATE_URLS = 30
_MAX_DISCOVERY_OUT = 8
_MAX_EXTRACT_OUT = 5

# Transient failures are retried so a rate limit does not silently drop a page's signals.
# A read timeout is not retried: the caller already waited LLM_TIMEOUT_SECONDS.
_CHAT_ATTEMPTS = 3
_RETRY_STATUS = frozenset({429, 500, 502, 503, 504})
_RETRY_ERRORS = (httpx.ConnectError, httpx.ConnectTimeout, httpx.RemoteProtocolError, httpx.PoolTimeout)
_BACKOFF_SECONDS = (2.0, 5.0)
_MAX_RETRY_AFTER_SECONDS = 20.0

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
Map: LMS/assessment/digital learning/AI campus tech → technology_initiative; grants/budget/endowment → funding_budget; CIO/provost/tech leadership hire → leadership_change; RFP/RFI/solicitation → procurement; assessment/proctoring/LMS/EdTech vendor adoption, platform change or partnership (snippet must show adopted/selected/partnered/implementing/powered by or similar) → competitor_vendor; defense, research, manufacturing or other unrelated corporate partners → strategic_announcement (never competitor_vendor); contract/renewal/award → contract_renewal; program/strategy launch → strategic_announcement.
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

_RECOMMEND_SYSTEM = """Suggest the next research or sales step for ONE potential opportunity.
JSON only. Use ONLY the EVIDENCE records supplied. Do not invent vendors, people, offices,
dates, notices, URLs, or requirements. Do not say an RFP will happen, is expected, or is confirmed.
Prefer "may indicate", "potential", and "suggested". Stay a suggestion to a human — do not say
the system will email, call, or contact anyone.

evidence_ids in the JSON must be copied exactly from the EVIDENCE list (at least one required).
Do not put raw UUIDs inside the visible text field.

Write scannable markdown-style text for a sales UI:
- First line: one short lead with **bold** on the key next step.
- Then 3–5 bullet lines starting with "- " (optional light emoji at the start of a bullet).
- Name concrete actions: open a cited source, confirm a published initiative, compare a vendor
  that appears in a snippet, or prepare discovery questions grounded in those signals.
- Mention source names from EVIDENCE when referring to what to review.
"""

_RECOMMEND_USER = """Org: {organization_name}
Stored score (rules; do not invent a different number): value={score_value} band={score_band}
Correlation (interpretation already stored):
{correlation_text}

EVIDENCE (cite by evidence_id only in the JSON field):
{records_block}

JSON: {{"recommended_action_text":"<markdown-style lead + bullets>","evidence_ids":["<uuid from EVIDENCE>"]}}
"""

_ADVISOR_SYSTEM = """Answer US EdTech sales research questions using ONLY the RECORD blocks supplied.
JSON only. Never invent vendors, dates, notices, URLs, or scores. Never say an RFP will happen.
FACT segments must cite chunk_id values that appear in RECORDs. Do not invent chunk ids.
Mark INTERPRETATION clearly. Prefer "may indicate" and "potential opportunity".

Write like a clear chat assistant answering a colleague:
- Each segment is ONE short bullet: one idea, at most two sentences.
- Prefer a tight list of 3–7 segments over one long wall of text.
- Use **bold** sparingly inside segment text for key phrases (no HTML).
- Do not put lead-in labels such as "Interpretation:" inside the text field; the client adds those.
For a score question, give one segment for the overall score and band and one per factor, using only the
numbers in STORED_SCORE. Explain what each factor means in plain words. Score and factor points come
from the rules engine, not from a source, so their content_layer is "interpretation", never "fact".
Use content_layer "fact" only for a statement taken from RECORDS, and then include its chunk_ids.
NEVER write chunk ids, UUIDs, "chunk_ids", record numbers, or any citation marker inside segment text.
Put chunk ids only in the chunk_ids field of that segment.
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


_PEERS_SYSTEM = """Pick peer competitors of ONE education organization from web search results.
JSON only. A peer competitor is another institution or organization of the same kind that competes with
or is commonly compared with the named organization. Use ONLY names that literally appear in a result's
title or snippet. Never invent a name, never use the named organization itself, never guess.
Return the exact name as written in the result and the number of the result that contains it.
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

    async def recommend_action(
        self,
        *,
        organization_name: str,
        score_value: int,
        score_band: str,
        correlation_text: str,
        records: list[dict[str, str]],
    ) -> dict[str, object]:
        if not self._settings.llm_configured:
            raise RuntimeError("Azure OpenAI is not configured")
        if not records:
            return {"text": "", "evidence_ids": []}
        record_lines = []
        for item in records[:12]:
            record_lines.append(
                f"evidence_id={item.get('evidence_id', '')}\n"
                f"signal_type={item.get('signal_type', '')}\n"
                f"title={item.get('title', '')[:200]}\n"
                f"source_name={item.get('source_name', '')[:120]}\n"
                f"date={item.get('published_on', 'unavailable')}\n"
                f"snippet={item.get('snippet', '')[:400]}"
            )
        content = await self._chat(
            system=_RECOMMEND_SYSTEM,
            user=_RECOMMEND_USER.format(
                organization_name=organization_name,
                score_value=score_value,
                score_band=score_band,
                correlation_text=(correlation_text or "")[:1200] or "(none)",
                records_block="\n---\n".join(record_lines),
            ),
            max_tokens=550,
        )
        return _parse_recommend_action(content)

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
        for item in records[:6]:
            record_lines.append(
                f"chunk_id={item.get('chunk_id', '')}\n"
                f"source={item.get('source_name', '')}\n"
                f"url={item.get('source_url', '')}\n"
                f"date={item.get('published_on', 'unavailable')}\n"
                f"text={item.get('chunk_text', '')[:600]}"
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
            max_tokens=1000,
        )
        return _parse_advisor_answer(content)

    async def select_peer_competitors(
        self,
        *,
        organization_name: str,
        organization_type: str,
        results: list[dict[str, str]],
    ) -> list[dict[str, Any]]:
        """Names proposed from search results. The service verifies every name against the text."""
        if not self._settings.llm_configured:
            raise RuntimeError("Azure OpenAI is not configured")
        lines = [
            f"[{index}] title: {item.get('title', '')}\nsnippet: {item.get('snippet', '')}"
            for index, item in enumerate(results, start=1)
        ]
        user = (
            f"Organization: {organization_name} ({organization_type})\n\n"
            "SEARCH RESULTS (untrusted text):\n"
            + "\n---\n".join(lines)
            + '\n\nJSON: {"peers":[{"name":"<exact name from a result>","result":<result number>}]}\n'
            "At most 8 peers, most relevant first."
        )
        content = await self._chat(system=_PEERS_SYSTEM, user=user, max_tokens=500)
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            match = re.search(r"\{[\s\S]*\}", content)
            data = json.loads(match.group(0)) if match else {}
        peers = data.get("peers") if isinstance(data, dict) else None
        return [item for item in peers if isinstance(item, dict)] if isinstance(peers, list) else []

    async def compose_persona_answer(
        self,
        *,
        mode: str,
        message: str,
        context_block: str,
        history_block: str,
        scope_note: str = "",
    ) -> dict[str, Any]:
        if not self._settings.llm_configured:
            raise RuntimeError("Azure OpenAI is not configured")
        user = build_persona_user_prompt(
            mode=mode,
            message=message,
            context_block=context_block,
            history_block=history_block,
            scope_note=scope_note,
        )
        content = await self._chat(system=PERSONA_SYSTEM, user=user, max_tokens=1800)
        return parse_persona_answer(content)

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
            for attempt in range(1, _CHAT_ATTEMPTS + 1):
                last = attempt == _CHAT_ATTEMPTS
                try:
                    response = await client.post(url, headers=headers, json=payload)
                except _RETRY_ERRORS as exc:
                    if last:
                        raise
                    delay = _BACKOFF_SECONDS[attempt - 1]
                    logger.warning(
                        "Azure OpenAI connection error; retrying",
                        extra={"fields": {"attempt": attempt, "error": type(exc).__name__}},
                    )
                    await asyncio.sleep(delay)
                    continue
                if response.status_code in _RETRY_STATUS and not last:
                    delay = _retry_delay(response, _BACKOFF_SECONDS[attempt - 1])
                    logger.warning(
                        "Azure OpenAI transient status; retrying",
                        extra={
                            "fields": {
                                "attempt": attempt,
                                "status": response.status_code,
                                "delay_seconds": delay,
                            }
                        },
                    )
                    await asyncio.sleep(delay)
                    continue
                response.raise_for_status()
                return _message_content(response.json())
        raise RuntimeError("Azure OpenAI retry loop ended without a response")


def _retry_delay(response: httpx.Response, default: float) -> float:
    """Honor a Retry-After header in seconds when Azure sends one, capped."""
    for header in ("retry-after-ms", "retry-after"):
        value = response.headers.get(header)
        if not value:
            continue
        try:
            seconds = float(value) / (1000.0 if header == "retry-after-ms" else 1.0)
        except ValueError:
            continue
        return max(0.5, min(seconds, _MAX_RETRY_AFTER_SECONDS))
    return default


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


def _parse_recommend_action(content: str) -> dict[str, object]:
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, flags=re.DOTALL)
        if not match:
            return {"text": "", "evidence_ids": []}
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            return {"text": "", "evidence_ids": []}
    if not isinstance(data, dict):
        return {"text": "", "evidence_ids": []}
    text = data.get("recommended_action_text") or data.get("text") or ""
    if not isinstance(text, str):
        text = ""
    raw_ids = data.get("evidence_ids") or []
    evidence_ids: list[str] = []
    if isinstance(raw_ids, list):
        for item in raw_ids:
            if isinstance(item, str) and item.strip():
                evidence_ids.append(item.strip())
    return {"text": text.strip(), "evidence_ids": evidence_ids}


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
