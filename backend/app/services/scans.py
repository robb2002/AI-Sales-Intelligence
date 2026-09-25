from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.ai.adapters import create_llm_adapter
from app.ai.adapters.base import LLMProviderAdapter
from app.core.config import Settings
from app.core.errors import NotFoundError, ValidationAppError
from app.ingestion.fetcher import Fetcher, create_http_client
from app.ingestion.limiter import HostLimiter
from app.repositories import organization_sources as organization_sources_repo
from app.repositories.organizations import Organization
from app.repositories.scans import ScanBatch, ScanRun
from app.services import sam_collection
from app.services.document_collection import collect_organization_documents
from app.services.document_indexing import index_documents
from app.services.opportunity_correlation import correlate_organization_opportunity
from app.services.sam_collection import SamBatchOutcome
from app.services.signal_dedup import dedupe_organization_signals
from app.services.signal_extraction import extract_organization_signals
from app.services.source_discovery import list_active_organizations, run_organization_discovery
from app.ai.adapters.embeddings import get_embedding_adapter

logger = logging.getLogger("app.services.scans")


class NoActiveOrganizationsError(ValidationAppError):
    message = "No active organizations are available to scan."


async def start_scan_all(
    session: AsyncSession,
    *,
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    requested_by_user_id: uuid.UUID | None = None,
) -> tuple[ScanBatch, list[ScanRun], list[uuid.UUID]]:
    orgs = await list_active_organizations(session)
    if not orgs:
        raise NoActiveOrganizationsError()

    batch = ScanBatch()
    session.add(batch)
    await session.flush()

    runs: list[ScanRun] = []
    to_start: list[uuid.UUID] = []

    for org in orgs:
        existing = await _active_scan_for_org(session, org.organization_id)
        if existing is not None:
            existing.batch_id = batch.batch_id
            runs.append(existing)
            continue

        run = ScanRun(
            batch_id=batch.batch_id,
            organization_id=org.organization_id,
            trigger="manual",
            requested_by_user_id=requested_by_user_id,
            status="queued",
            stage="discovering",
            sources=[],
        )
        session.add(run)
        await session.flush()
        runs.append(run)
        to_start.append(run.scan_id)

    await session.commit()
    for run in runs:
        await session.refresh(run)
    await session.refresh(batch)

    if to_start:
        asyncio.create_task(
            _run_batch(
                session_factory=session_factory,
                settings=settings,
                scan_ids=to_start,
            )
        )

    return batch, runs, to_start


async def start_scan_for_organization(
    session: AsyncSession,
    organization_id: uuid.UUID,
    *,
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    requested_by_user_id: uuid.UUID | None = None,
) -> tuple[ScanRun, Organization, bool]:
    org = await session.get(Organization, organization_id)
    if org is None:
        raise NotFoundError("organization")

    existing = await _active_scan_for_org(session, organization_id)
    if existing is not None:
        return existing, org, True

    if org.tracking_status != "active":
        raise ValidationAppError(
            message="Activate this organization before running Scan Now.",
            details={"tracking_status": "inactive"},
        )

    run = ScanRun(
        batch_id=None,
        organization_id=organization_id,
        trigger="manual",
        requested_by_user_id=requested_by_user_id,
        status="queued",
        stage="discovering",
        sources=[],
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)

    asyncio.create_task(
        _run_batch(
            session_factory=session_factory,
            settings=settings,
            scan_ids=[run.scan_id],
        )
    )
    return run, org, False


async def get_batch_detail(
    session: AsyncSession, batch_id: uuid.UUID
) -> tuple[ScanBatch, list[ScanRun], list[Organization]]:
    batch = await session.get(ScanBatch, batch_id)
    if batch is None:
        raise NotFoundError("scan_batch")
    result = await session.execute(
        select(ScanRun).where(ScanRun.batch_id == batch_id).order_by(ScanRun.created_at)
    )
    runs = list(result.scalars().all())
    org_ids = [run.organization_id for run in runs]
    orgs: list[Organization] = []
    if org_ids:
        org_result = await session.execute(
            select(Organization).where(Organization.organization_id.in_(org_ids))
        )
        orgs = list(org_result.scalars().all())
    return batch, runs, orgs


async def get_scan_detail(session: AsyncSession, scan_id: uuid.UUID) -> tuple[ScanRun, Organization]:
    scan = await session.get(ScanRun, scan_id)
    if scan is None:
        raise NotFoundError("scan")
    org = await session.get(Organization, scan.organization_id)
    if org is None:
        raise NotFoundError("organization")
    return scan, org


async def mark_interrupted_on_startup(session_factory: async_sessionmaker[AsyncSession]) -> None:
    async with session_factory() as session:
        await organization_sources_repo.reset_interrupted_extractions(session)
        result = await session.execute(
            select(ScanRun).where(ScanRun.status.in_(("queued", "running")))
        )
        rows = list(result.scalars().all())
        now = datetime.now(timezone.utc)
        for row in rows:
            row.status = "interrupted"
            row.stage = None
            row.finished_at = now
            row.error_detail = "Server restarted during this scan"
        await session.commit()
        if rows:
            logger.info("Marked interrupted scans", extra={"fields": {"count": len(rows)}})


async def _active_scan_for_org(session: AsyncSession, organization_id: uuid.UUID) -> ScanRun | None:
    result = await session.execute(
        select(ScanRun).where(
            ScanRun.organization_id == organization_id,
            ScanRun.status.in_(("queued", "running")),
        )
    )
    return result.scalar_one_or_none()


async def _run_batch(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    settings: Settings,
    scan_ids: list[uuid.UUID],
) -> None:
    try:
        llm = create_llm_adapter(settings)
    except Exception:
        logger.exception("LLM adapter unavailable")
        async with session_factory() as session:
            for scan_id in scan_ids:
                scan = await session.get(ScanRun, scan_id)
                if scan is None:
                    continue
                scan.status = "failed"
                scan.stage = None
                scan.error_detail = "LLM provider is not configured"
                scan.finished_at = datetime.now(timezone.utc)
            await session.commit()
        return

    orgs_by_id: dict[uuid.UUID, Organization] = {}
    async with session_factory() as session:
        for scan_id in scan_ids:
            scan = await session.get(ScanRun, scan_id)
            if scan is None:
                continue
            org = await session.get(Organization, scan.organization_id)
            if org is not None:
                orgs_by_id[org.organization_id] = org

    # SAM.gov runs once for the batch in parallel with org website work starting.
    sam_task = asyncio.create_task(
        sam_collection.fetch_sam_for_batch(
            session_factory,
            settings=settings,
            organizations=list(orgs_by_id.values()),
        )
    )

    semaphore = asyncio.Semaphore(max(1, settings.scan_org_concurrency))
    limiter = HostLimiter()

    async with create_http_client(settings) as client:
        fetcher = Fetcher(client, limiter, settings)

        async def run_one(scan_id: uuid.UUID) -> None:
            async with semaphore:
                await _run_organization(
                    session_factory=session_factory,
                    settings=settings,
                    llm=llm,
                    fetcher=fetcher,
                    scan_id=scan_id,
                    sam_task=sam_task,
                )

        await asyncio.gather(*[run_one(scan_id) for scan_id in scan_ids])

    if not sam_task.done():
        await sam_task


async def _run_organization(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    settings: Settings,
    llm: LLMProviderAdapter,
    fetcher: Fetcher,
    scan_id: uuid.UUID,
    sam_task: asyncio.Task[SamBatchOutcome],
) -> None:
    """Website discovery/collection for one org, while SAM.gov search runs for the batch."""
    async with session_factory() as session:
        scan = await session.get(ScanRun, scan_id)
        if scan is None:
            return
        org = await session.get(Organization, scan.organization_id)
        if org is None:
            return
        try:
            pages = await run_organization_discovery(
                session, settings=settings, llm=llm, fetcher=fetcher, scan=scan, org=org
            )
            sam_outcome = await sam_task
            sam_changed_ids = await sam_collection.store_sam_notices_for_organization(
                session,
                scan=scan,
                org=org,
                notices=sam_outcome.by_organization.get(org.organization_id, []),
                batch_source_row=sam_outcome.source_row,
            )
            await session.commit()

            if pages is None:
                # Discovery already marked the run failed; keep SAM rows and soften to partial
                # when SAM matched notices for this organization.
                if sam_outcome.by_organization.get(org.organization_id):
                    scan.status = "partial"
                    scan.error_detail = (
                        "Website discovery failed; SAM.gov notices were still stored"
                    )
                    scan.stage = None
                    if scan.finished_at is None:
                        scan.finished_at = datetime.now(timezone.utc)
                    await session.commit()
                return

            website = await collect_organization_documents(
                session, settings=settings, fetcher=fetcher, scan=scan, org=org, pages=pages
            )

            # Only new/changed document bodies go to the LLM (unchanged hashes are skipped).
            extract_ids = list(dict.fromkeys([*sam_changed_ids, *website.changed_document_ids]))

            try:
                embedder = get_embedding_adapter(settings)
                indexed = await index_documents(
                    session,
                    settings=settings,
                    embedder=embedder,
                    organization=org,
                    document_ids=extract_ids,
                )
                if indexed:
                    scan.sources = list(scan.sources or []) + [
                        {
                            "source_name": "Advisor index",
                            "status": "succeeded",
                            "detail": f"{indexed} chunks embedded",
                        }
                    ]
                await session.commit()
            except Exception:
                logger.exception("Document indexing failed")
                scan.sources = list(scan.sources or []) + [
                    {
                        "source_name": "Advisor index",
                        "status": "failed",
                        "detail": "unexpected_error",
                    }
                ]
                await session.commit()

            try:
                await extract_organization_signals(
                    session,
                    llm=llm,
                    scan=scan,
                    org=org,
                    document_ids=extract_ids,
                )
                await session.commit()
            except Exception:
                logger.exception("Signal extraction failed")
                scan.sources = list(scan.sources or []) + [
                    {
                        "source_name": "Signal extraction",
                        "status": "failed",
                        "detail": "unexpected_error",
                    }
                ]
                await session.commit()

            try:
                await dedupe_organization_signals(session, scan=scan, org=org)
                await session.commit()
            except Exception:
                logger.exception("Signal dedup failed")
                scan.sources = list(scan.sources or []) + [
                    {
                        "source_name": "Signal dedup",
                        "status": "failed",
                        "detail": "unexpected_error",
                    }
                ]
                await session.commit()

            try:
                await correlate_organization_opportunity(
                    session, llm=llm, scan=scan, org=org
                )
                await session.commit()
            except Exception:
                logger.exception("Opportunity correlation failed")
                scan.sources = list(scan.sources or []) + [
                    {
                        "source_name": "Opportunity correlation",
                        "status": "failed",
                        "detail": "unexpected_error",
                    }
                ]
                await session.commit()

            sam_failed = any(
                isinstance(row, dict)
                and row.get("source_name") == "SAM.gov"
                and row.get("status") == "failed"
                for row in (scan.sources or [])
            )
            extract_failed = any(
                isinstance(row, dict)
                and row.get("source_name") == "Signal extraction"
                and row.get("status") == "failed"
                for row in (scan.sources or [])
            )
            dedup_failed = any(
                isinstance(row, dict)
                and row.get("source_name") == "Signal dedup"
                and row.get("status") == "failed"
                for row in (scan.sources or [])
            )
            correlate_failed = any(
                isinstance(row, dict)
                and row.get("source_name") == "Opportunity correlation"
                and row.get("status") == "failed"
                for row in (scan.sources or [])
            )
            website_partial = website.failed_pages > 0 and (
                website.attempted_pages - website.failed_pages + website.reused_pages > 0
            )
            website_failed = (
                website.failed_pages > 0
                and not website_partial
                and website.attempted_pages > 0
            )

            if website_failed and sam_failed:
                scan.status = "failed"
                scan.error_detail = "Website and SAM.gov collection both failed"
            elif website_failed and not sam_outcome.ok:
                scan.status = "failed"
                scan.error_detail = "No approved page could be collected"
            elif (
                website_failed
                or website_partial
                or sam_failed
                or extract_failed
                or dedup_failed
                or correlate_failed
            ):
                scan.status = "partial"
                scan.error_detail = None
            else:
                scan.status = "succeeded"
                scan.error_detail = None

            scan.stage = None
            scan.finished_at = datetime.now(timezone.utc)
            await session.commit()
        except Exception:
            logger.exception("Organization scan failed")
            await session.rollback()
            await organization_sources_repo.reset_interrupted_extractions(
                session, organization_id=org.organization_id
            )
            scan = await session.get(ScanRun, scan_id)
            if scan is not None:
                scan.status = "failed"
                scan.stage = None
                scan.error_detail = "Scan stopped by an unexpected error"
                scan.finished_at = datetime.now(timezone.utc)
                await session.commit()
