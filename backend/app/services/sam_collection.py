"""SAM.gov collection for Scan All / Scan Now.

Shared batch search first (DATA_SOURCES.md §8). If nothing matches a tracked org and
quota remains, at most a few documented `title` searches (one per unmatched org, capped).
Application cap of 10 requests / 24 hours — not SAM.gov's official quota.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.ingestion.collectors import sam_gov as sam_api
from app.repositories import documents as documents_repo
from app.repositories import source_requests as source_requests_repo
from app.repositories import sources as sources_repo
from app.repositories.organizations import Organization
from app.repositories.scans import ScanRun

logger = logging.getLogger("app.services.sam_collection")

# Extra title searches after the shared page, still "a few" under DATA_SOURCES.md §8.
_MAX_TITLE_SEARCHES = 2


@dataclass
class SamBatchOutcome:
    by_organization: dict[uuid.UUID, list[sam_api.SamNotice]] = field(default_factory=dict)
    source_row: dict = field(default_factory=dict)
    ok: bool = False


async def fetch_sam_for_batch(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    settings: Settings,
    organizations: list[Organization],
) -> SamBatchOutcome:
    outcome = SamBatchOutcome()
    if not organizations:
        outcome.source_row = {
            "source_name": "SAM.gov",
            "status": "failed",
            "detail": "no_organizations",
        }
        return outcome

    if not settings.sam_gov_api_key.strip():
        outcome.source_row = {
            "source_name": "SAM.gov",
            "status": "failed",
            "detail": "missing_api_key",
        }
        return outcome

    cap = max(0, settings.sam_gov_daily_request_cap)
    searches = 0
    total_returned = 0
    all_notices: list[sam_api.SamNotice] = []

    async with session_factory() as session:
        used = await source_requests_repo.count_recent(session, source_key=sam_api.SOURCE_KEY)
        if used >= cap:
            outcome.source_row = {
                "source_name": "SAM.gov",
                "status": "failed",
                "detail": (
                    f"application_cap_exhausted ({used}/{cap} in 24h); "
                    "reusing stored documents only"
                ),
            }
            await source_requests_repo.record(
                session,
                source_key=sam_api.SOURCE_KEY,
                outcome="quota_blocked",
                detail=f"used={used} cap={cap}",
            )
            await session.commit()
            return outcome
        remaining = cap - used

    async with sam_api.create_sam_client(settings) as client:
        shared = await _search_and_log(
            session_factory, client=client, settings=settings, title=None
        )
        if shared is None:
            outcome.source_row = {
                "source_name": "SAM.gov",
                "status": "failed",
                "detail": "search_failed",
            }
            return outcome
        if not shared.ok:
            outcome.source_row = {
                "source_name": "SAM.gov",
                "status": "failed",
                "detail": shared.reason or "search_failed",
            }
            return outcome

        searches += 1
        remaining -= 1 if shared.request_counted else 0
        total_returned += len(shared.notices)
        all_notices.extend(shared.notices)

        by_org: dict[uuid.UUID, list[sam_api.SamNotice]] = {
            org.organization_id: [
                n for n in all_notices if sam_api.notice_matches_organization(n, org.name)
            ]
            for org in organizations
        }

        unmatched = [org for org in organizations if not by_org.get(org.organization_id)]
        title_searches = 0
        for org in unmatched:
            if remaining <= 0 or title_searches >= _MAX_TITLE_SEARCHES:
                break
            needles = sam_api.organization_match_needles(org.name)
            title = needles[0] if needles else None
            if not title:
                continue
            titled = await _search_and_log(
                session_factory, client=client, settings=settings, title=title
            )
            if titled is None or not titled.ok:
                continue
            searches += 1
            title_searches += 1
            if titled.request_counted:
                remaining -= 1
            total_returned += len(titled.notices)
            hits = [
                n for n in titled.notices if sam_api.notice_matches_organization(n, org.name)
            ]
            if hits:
                by_org[org.organization_id] = hits

    matched = sum(len(v) for v in by_org.values())
    outcome.by_organization = {k: v for k, v in by_org.items() if v}
    outcome.ok = True
    outcome.source_row = {
        "source_name": "SAM.gov",
        "status": "succeeded",
        "detail": (
            f"{searches} search(es), {total_returned} notices returned, "
            f"{matched} matched to tracked organizations"
        ),
    }
    return outcome


async def store_sam_notices_for_organization(
    session: AsyncSession,
    *,
    scan: ScanRun,
    org: Organization,
    notices: list[sam_api.SamNotice],
    batch_source_row: dict,
) -> list[uuid.UUID]:
    """Persist matched notices. Returns document ids that were inserted or updated."""
    source_rows = list(scan.sources or [])
    changed_ids: list[uuid.UUID] = []

    if batch_source_row.get("status") == "failed":
        # One shared failure row per org scan so the UI shows SAM did not run.
        source_rows.append(dict(batch_source_row))
        scan.sources = source_rows
        await session.flush()
        return changed_ids

    if not notices:
        source_rows.append(
            {
                "source_name": "SAM.gov",
                "status": "succeeded",
                "detail": "0 notices matched this organization",
            }
        )
        scan.sources = source_rows
        await session.flush()
        return changed_ids

    source = await sources_repo.get_by_key(session, sam_api.SOURCE_KEY)
    if source is None:
        source_rows.append(
            {
                "source_name": "SAM.gov",
                "status": "failed",
                "detail": "registry_row_missing",
            }
        )
        scan.sources = source_rows
        await session.flush()
        return changed_ids

    counts = {"inserted": 0, "updated": 0, "unchanged": 0}
    for notice in notices:
        status, document_id = await documents_repo.save_api_document(
            session,
            source_id=source.source_id,
            organization_id=org.organization_id,
            external_id=notice.notice_id,
            source_url=sam_api.EVIDENCE_ENTRY_URL,
            title=notice.title,
            body_text=notice.body_text,
            content_hash=notice.content_hash,
            published_on=notice.published_on,
            http_status=notice.http_status,
            retrieved_at=notice.retrieved_at,
        )
        counts[status] += 1
        if status in ("inserted", "updated"):
            changed_ids.append(document_id)

    changed = counts["inserted"] + counts["updated"]
    source_rows.append(
        {
            "source_name": "SAM.gov",
            "status": "succeeded",
            "detail": (
                f"{counts['inserted']} new, {counts['updated']} updated, "
                f"{counts['unchanged']} unchanged"
            ),
        }
    )
    scan.sources = source_rows
    scan.documents_collected = int(scan.documents_collected or 0) + changed
    await session.flush()
    return changed_ids


async def _search_and_log(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    client: httpx.AsyncClient,
    settings: Settings,
    title: str | None,
) -> sam_api.SamSearchResult | None:
    try:
        result = await sam_api.search_opportunities(client, settings, title=title)
    except Exception:
        logger.exception("SAM.gov search crashed")
        return None

    if result.request_counted:
        async with session_factory() as session:
            await source_requests_repo.record(
                session,
                source_key=sam_api.SOURCE_KEY,
                outcome=(
                    "ok"
                    if result.ok
                    else "rejected"
                    if result.http_status in (401, 403, 429)
                    else "error"
                ),
                http_status=result.http_status,
                detail=result.reason,
            )
            await session.commit()
    return result
