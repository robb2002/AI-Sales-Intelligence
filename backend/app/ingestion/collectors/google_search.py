"""Google Programmable Search (Custom Search JSON API) client, DATA_SOURCES.md §8.

Official API only. It is never used to scrape google.com. The caller enforces the application
daily cap first. Titles, snippets and links come from the API response unchanged.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

from app.core.config import Settings

logger = logging.getLogger("app.ingestion.collectors.google_search")

SOURCE_KEY = "google_search"
_MAX_RESULTS = 10


@dataclass(frozen=True)
class SearchResult:
    title: str
    snippet: str
    link: str


@dataclass(frozen=True)
class SearchOutcome:
    ok: bool
    results: list[SearchResult]
    http_status: int | None
    reason: str | None
    request_counted: bool


def create_search_client(settings: Settings) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        headers={"User-Agent": settings.http_user_agent, "Accept": "application/json"},
        timeout=httpx.Timeout(settings.http_timeout_seconds, connect=10.0),
    )


async def search(client: httpx.AsyncClient, settings: Settings, query: str) -> SearchOutcome:
    """One API request. Returns at most ten results with an https link."""
    if not settings.google_search_configured:
        return SearchOutcome(False, [], None, "not_configured", False)

    params = {
        "key": settings.google_search_api_key.strip(),
        "cx": settings.google_search_engine_id.strip(),
        "q": query,
        "num": _MAX_RESULTS,
        "hl": "en",
        "gl": "us",
    }
    try:
        response = await client.get(settings.google_search_url, params=params)
    except httpx.HTTPError as exc:
        logger.warning("Google search request failed: %s", type(exc).__name__)
        return SearchOutcome(False, [], None, "network_error", True)

    if response.status_code >= 400:
        reason = f"http_{response.status_code}"
        try:
            body = response.json()
            message = (body.get("error") or {}).get("message") if isinstance(body, dict) else None
            if message:
                reason = f"{reason}: {str(message)[:160]}"
        except ValueError:
            pass
        return SearchOutcome(False, [], response.status_code, reason, True)

    try:
        payload = response.json()
    except ValueError:
        return SearchOutcome(False, [], response.status_code, "invalid_json", True)

    results: list[SearchResult] = []
    for item in payload.get("items") or []:
        if not isinstance(item, dict):
            continue
        link = str(item.get("link") or "").strip()
        title = str(item.get("title") or "").strip()
        snippet = " ".join(str(item.get("snippet") or "").split())
        if link.startswith("https://") and (title or snippet):
            results.append(SearchResult(title=title, snippet=snippet, link=link))
    return SearchOutcome(True, results[:_MAX_RESULTS], response.status_code, None, True)
