"""Peer competitors of a tracked organization from a web search (DATA_SOURCES §8).

Update runs one Google Programmable Search request, asks the model to pick competitor names, then
KEEPS ONLY names that literally appear in a result's title or snippet. The stored snippet and link
are the search result's own. The top 5 replace the saved set in one transaction, so a failure keeps
the previous list. Context for a rep; never a signal, score, or opportunity.
"""

from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.adapters.azure_openai import AzureOpenAIAdapter
from app.core.config import Settings
from app.core.errors import (
    SearchFailedError,
    SearchNotConfiguredError,
    SearchRateLimitedError,
    ValidationAppError,
)
from app.ingestion.collectors import google_search
from app.repositories import competitors as competitors_repo
from app.repositories import organization_peer_competitors as peers_repo
from app.repositories import source_requests as source_requests_repo
from app.repositories.organization_peer_competitors import OrganizationPeerCompetitor
from app.repositories.organizations import Organization
from app.schemas.peer_competitors import PeerCompetitorItem, PeerCompetitorsResponse

logger = logging.getLogger("app.services.peer_competitors")

_TOP_N = 5
_QUERY_KIND = {
    "university": "peer universities and competitors",
    "college": "peer colleges and competitors",
    "k12_district": "peer school districts and competitors",
    "public_sector_education": "peer education agencies and competitors",
}


def build_query(org: Organization) -> str:
    return f'"{org.name}" {_QUERY_KIND.get(org.organization_type, "peer institutions and competitors")}'


async def get_saved(
    session: AsyncSession, *, settings: Settings, org: Organization
) -> PeerCompetitorsResponse:
    rows = await peers_repo.list_for_organization(session, org.organization_id)
    return _response(org.organization_id, settings, rows)


async def refresh(
    session: AsyncSession,
    *,
    settings: Settings,
    llm: AzureOpenAIAdapter,
    org: Organization,
) -> PeerCompetitorsResponse:
    if org.market_role != "target":
        raise ValidationAppError(message="Peer competitors are only searched for target organizations.")
    if not settings.google_search_configured:
        raise SearchNotConfiguredError()
    if not settings.llm_configured:
        raise SearchFailedError(message="The AI provider is not configured, so names cannot be picked.")

    used = await source_requests_repo.count_recent(session, source_key=google_search.SOURCE_KEY)
    if used >= max(0, settings.google_search_daily_request_cap):
        await source_requests_repo.record(
            session,
            source_key=google_search.SOURCE_KEY,
            outcome="quota_blocked",
            detail=f"used={used} cap={settings.google_search_daily_request_cap}",
        )
        await session.commit()
        raise SearchRateLimitedError()

    query = build_query(org)
    async with google_search.create_search_client(settings) as client:
        outcome = await google_search.search(client, settings, query)

    if outcome.request_counted:
        await source_requests_repo.record(
            session,
            source_key=google_search.SOURCE_KEY,
            outcome="ok"
            if outcome.ok
            else "rejected"
            if outcome.http_status in (401, 403, 429)
            else "error",
            http_status=outcome.http_status,
            detail=outcome.reason,
        )
        await session.commit()
    if not outcome.ok:
        raise SearchFailedError(details={"reason": outcome.reason or "search_failed"})
    # Only results that are about this organization are used; everything else is discarded.
    relevant = [r for r in outcome.results if _mentions_org(org, r)]
    if not relevant:
        raise SearchFailedError(
            message="The search returned nothing about this organization. The previous list is unchanged."
        )
    outcome = google_search.SearchOutcome(True, relevant, outcome.http_status, None, True)

    try:
        proposed = await llm.select_peer_competitors(
            organization_name=org.name,
            organization_type=org.organization_type,
            results=[{"title": r.title, "snippet": r.snippet} for r in outcome.results],
        )
    except Exception:
        logger.exception("Peer competitor selection failed")
        raise SearchFailedError(message="Names could not be picked from the results.") from None

    tracked_competitors = await competitors_repo.competitor_organizations(session)
    blocked = {_normalize(c.name) for c in tracked_competitors if c.name}
    ranked = rank_peers(org, outcome.results, proposed, blocked_competitor_names=blocked)
    if not ranked:
        raise SearchFailedError(
            message="The search returned no clear peer competitors. The previous list is unchanged."
        )

    now = datetime.now(timezone.utc)
    rows = [
        OrganizationPeerCompetitor(
            organization_id=org.organization_id,
            rank=rank,
            competitor_name=name,
            source_title=result.title or None,
            source_url=result.link,
            snippet=text,
            search_query=query,
            retrieved_at=now,
        )
        for rank, (name, result, text) in enumerate(ranked, start=1)
    ]
    await peers_repo.replace_for_organization(session, org.organization_id, rows)
    await session.commit()
    return _response(org.organization_id, settings, rows)


def rank_peers(
    org: Organization,
    results: list[google_search.SearchResult],
    proposed: list[dict],
    *,
    blocked_competitor_names: set[str] | None = None,
) -> list[tuple[str, google_search.SearchResult, str]]:
    """Verified, deduplicated, ranked (name, result, verbatim text). No model text is trusted.

    A name is kept only if it appears (case-insensitive) in the title or snippet of the result the
    model pointed at. Tracked EdTech competitor org names are dropped (peers are institutions).
    It ranks higher the more results mention it, then by earliest result.
    """
    own = _normalize(org.name)
    blocked = blocked_competitor_names or set()

    seen: set[str] = set()
    candidates: list[tuple[str, int, google_search.SearchResult, str]] = []
    for item in proposed:
        name = " ".join(str(item.get("name") or "").split()).strip(" ,.;:-")
        index = item.get("result")
        if not name or len(name) < 3 or not isinstance(index, int) or not 1 <= index <= len(results):
            continue
        key = _normalize(name)
        if not key or key in seen or key == own or key in own or own in key:
            continue
        if _is_blocked_competitor_name(key, blocked):
            continue
        result = results[index - 1]
        text = _verbatim_text(name, result)
        if text is None:
            continue
        seen.add(key)
        candidates.append((name, index, result, text))

    def mentions(name: str) -> int:
        needle = name.lower()
        return sum(1 for r in results if needle in f"{r.title} {r.snippet}".lower())

    candidates.sort(key=lambda c: (-mentions(c[0]), c[1]))
    return [(name, result, text) for name, _index, result, text in candidates[:_TOP_N]]


def _is_blocked_competitor_name(normalized_name: str, blocked: set[str]) -> bool:
    """True when the proposed peer matches a tracked competitor organization name."""
    if not blocked or not normalized_name:
        return False
    if normalized_name in blocked:
        return True
    return any(
        normalized_name == b
        or (len(b) >= 4 and (b in normalized_name or normalized_name in b))
        for b in blocked
    )


def _mentions_org(org: Organization, result: google_search.SearchResult) -> bool:
    text = _normalize(f"{result.title} {result.snippet}")
    name = _normalize(org.name)
    needles = {name}
    for suffix in (" university", " college"):
        if name.endswith(suffix) and len(name) > len(suffix) + 3:
            needles.add(name[: -len(suffix)])
    return any(needle in text for needle in needles if len(needle) >= 4)


def _verbatim_text(name: str, result: google_search.SearchResult) -> str | None:
    needle = name.lower()
    if needle in result.snippet.lower():
        return result.snippet
    if needle in result.title.lower():
        return result.title
    return None


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", value.lower())).strip()


def _response(
    organization_id: uuid.UUID, settings: Settings, rows: list[OrganizationPeerCompetitor]
) -> PeerCompetitorsResponse:
    return PeerCompetitorsResponse(
        organization_id=organization_id,
        configured=settings.google_search_configured,
        last_updated_at=max((row.retrieved_at for row in rows), default=None),
        search_query=rows[0].search_query if rows else None,
        data_origin="live",
        peers=[
            PeerCompetitorItem(
                rank=row.rank,
                name=row.competitor_name,
                source_title=row.source_title,
                source_url=row.source_url,
                snippet=row.snippet,
                retrieved_at=row.retrieved_at,
            )
            for row in sorted(rows, key=lambda r: r.rank)
        ],
    )
