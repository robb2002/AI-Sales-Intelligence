"""USAspending collection for Scan Now / Scan All (DATA_SOURCES.md §3).

Runs after SAM.gov and website collection. Failures never fail the scan.
Only TARGET organizations that resolve to exactly one compatible recipient are
collected, at most once per organization per 24 hours.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.ingestion.collectors import usaspending as usa_api
from app.repositories import documents as documents_repo
from app.repositories import source_requests as source_requests_repo
from app.repositories import sources as sources_repo
from app.repositories.documents import Document
from app.repositories.organizations import Organization
from app.repositories.scans import ScanRun

logger = logging.getLogger("app.services.usaspending_collection")


async def collect_usaspending_for_organization(
    session: AsyncSession,
    *,
    settings: Settings,
    scan: ScanRun,
    org: Organization,
) -> list[uuid.UUID]:
    """Store award documents for one org. Returns changed document ids. Never raises."""
    source_rows = list(scan.sources or [])
    changed_ids: list[uuid.UUID] = []

    if not settings.usaspending_enabled:
        source_rows.append(
            {
                "source_name": "USAspending.gov",
                "status": "failed",
                "detail": "disabled",
            }
        )
        scan.sources = source_rows
        await session.flush()
        return changed_ids

    if org.market_role != "target":
        source_rows.append(
            {
                "source_name": "USAspending.gov",
                "status": "succeeded",
                "detail": "skipped_competitor",
            }
        )
        scan.sources = source_rows
        await session.flush()
        return changed_ids

    source = await sources_repo.get_by_key(session, usa_api.SOURCE_KEY)
    if source is None:
        source_rows.append(
            {
                "source_name": "USAspending.gov",
                "status": "failed",
                "detail": "registry_row_missing",
            }
        )
        scan.sources = source_rows
        await session.flush()
        return changed_ids

    if await _collected_within_day(session, source_id=source.source_id, organization_id=org.organization_id):
        source_rows.append(
            {
                "source_name": "USAspending.gov",
                "status": "succeeded",
                "detail": "skipped_already_collected_within_24h",
            }
        )
        scan.sources = source_rows
        await session.flush()
        return changed_ids

    try:
        async with usa_api.create_usa_client(settings) as client:
            resolved = await usa_api.resolve_recipient(client, organization_name=org.name)
            if resolved.request_counted:
                await source_requests_repo.record(
                    session,
                    source_key=usa_api.SOURCE_KEY,
                    outcome="ok" if resolved.ok and resolved.recipient_name else "rejected",
                    http_status=resolved.http_status,
                    detail=f"org={org.organization_id};{resolved.reason or 'resolved'}",
                )

            if not resolved.ok:
                source_rows.append(
                    {
                        "source_name": "USAspending.gov",
                        "status": "failed",
                        "detail": resolved.reason or "autocomplete_failed",
                    }
                )
                scan.sources = source_rows
                await session.flush()
                return changed_ids

            if resolved.recipient_name is None:
                detail = resolved.reason or "no_recipient"
                if resolved.candidates:
                    detail = f"{detail}; candidates={len(resolved.candidates)}"
                source_rows.append(
                    {
                        "source_name": "USAspending.gov",
                        "status": "succeeded",
                        "detail": detail,
                    }
                )
                scan.sources = source_rows
                await session.flush()
                return changed_ids

            awards_result = await usa_api.search_awards_for_recipient(
                client,
                recipient_name=resolved.recipient_name,
                max_awards=max(1, settings.usaspending_max_awards_per_org),
            )
            if awards_result.request_counted:
                await source_requests_repo.record(
                    session,
                    source_key=usa_api.SOURCE_KEY,
                    outcome="ok" if awards_result.ok else "error",
                    http_status=awards_result.http_status,
                    detail=f"org={org.organization_id};awards",
                )

            if not awards_result.ok:
                source_rows.append(
                    {
                        "source_name": "USAspending.gov",
                        "status": "failed",
                        "detail": awards_result.reason or "search_failed",
                    }
                )
                scan.sources = source_rows
                await session.flush()
                return changed_ids

            if not awards_result.awards:
                source_rows.append(
                    {
                        "source_name": "USAspending.gov",
                        "status": "succeeded",
                        "detail": (
                            f"recipient={resolved.recipient_name}; 0 awards in window"
                        ),
                    }
                )
                scan.sources = source_rows
                await session.flush()
                return changed_ids

            counts = {"inserted": 0, "updated": 0, "unchanged": 0}
            for award in awards_result.awards:
                status, document_id = await documents_repo.save_api_document(
                    session,
                    source_id=source.source_id,
                    organization_id=org.organization_id,
                    external_id=award.external_id,
                    source_url=usa_api.EVIDENCE_ENTRY_URL,
                    title=award.title,
                    body_text=award.body_text,
                    content_hash=award.content_hash,
                    published_on=award.published_on,
                    http_status=award.http_status,
                    retrieved_at=award.retrieved_at,
                )
                counts[status] += 1
                if status in ("inserted", "updated"):
                    changed_ids.append(document_id)

            changed = counts["inserted"] + counts["updated"]
            source_rows.append(
                {
                    "source_name": "USAspending.gov",
                    "status": "succeeded",
                    "detail": (
                        f"recipient={resolved.recipient_name}; "
                        f"{counts['inserted']} new, {counts['updated']} updated, "
                        f"{counts['unchanged']} unchanged"
                    ),
                }
            )
            scan.sources = source_rows
            scan.documents_collected = int(scan.documents_collected or 0) + changed
            await session.flush()
            return changed_ids
    except Exception:
        logger.exception("USAspending collection crashed for %s", org.organization_id)
        source_rows.append(
            {
                "source_name": "USAspending.gov",
                "status": "failed",
                "detail": "unexpected_error",
            }
        )
        scan.sources = source_rows
        await session.flush()
        return []


async def _collected_within_day(
    session: AsyncSession, *, source_id: uuid.UUID, organization_id: uuid.UUID
) -> bool:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    latest = await session.scalar(
        select(func.max(Document.retrieved_at)).where(
            Document.source_id == source_id,
            Document.organization_id == organization_id,
        )
    )
    return latest is not None and latest >= cutoff
