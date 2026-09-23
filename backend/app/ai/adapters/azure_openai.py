from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx

from app.ai.adapters.base import SourceCandidate
from app.core.config import Settings
from app.repositories.organization_sources import PAGE_CATEGORIES

logger = logging.getLogger("app.ai.azure_openai")

_DISCOVERY_SYSTEM = """You are a source discovery agent for an AI Sales Intelligence system.
Return ONLY valid JSON.
You MUST select URLs only from the provided candidate_urls list.
Never invent a URL. Never add a host that is not already in candidate_urls.
If unsure, return fewer URLs.
"""

_DISCOVERY_USER = """Organization: {organization_name}
Official domain: {official_domain}

Select the best publicly useful pages from candidate_urls for sales intelligence
(procurement, technology, digital learning, assessment, funding, leadership,
strategic initiatives, partnerships).

candidate_urls:
{candidate_urls}

Rules:
- Every returned url MUST appear exactly in candidate_urls (copy/paste only).
- Do not invent URLs.
- Prefer at most 8 high-confidence pages.
- page_category must be one of: {categories}

Respond with JSON only:
{{"candidates":[{{"url":"https://...","title":"...","page_category":"technology","reason":"..."}}]}}
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

        endpoint = self._settings.azure_openai_endpoint.rstrip("/")
        deployment = self._settings.llm_model
        api_version = self._settings.azure_openai_api_version
        url = (
            f"{endpoint}/openai/deployments/{deployment}/chat/completions"
            f"?api-version={api_version}"
        )
        listed = "\n".join(f"- {item}" for item in allowlist[:40])
        payload = {
            "messages": [
                {"role": "system", "content": _DISCOVERY_SYSTEM},
                {
                    "role": "user",
                    "content": _DISCOVERY_USER.format(
                        organization_name=organization_name,
                        official_domain=official_domain,
                        candidate_urls=listed,
                        categories=", ".join(PAGE_CATEGORIES),
                    ),
                },
            ],
            "temperature": 0,
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

        content = _message_content(body)
        return _parse_candidates(content, allowlist=set(allowlist))


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
    # Normalize allowlist for matching invented variants of the same URL.
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
            # Hallucinated / off-list URL — drop.
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
    return results


def _loose_key(url: str) -> str:
    return url.strip().rstrip("/").lower().split("#", 1)[0]
