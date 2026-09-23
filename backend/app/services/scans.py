from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.ai.adapters import create_llm_adapter
from app.core.config import Settings
from app.core.errors import NotFoundError, ValidationAppError
from app.repositories.organizations import Organization
from app.repositories.scans import ScanBatch, ScanRun
from app.services.source_discovery import list_active_organizations, run_organization_discovery

logger = logging.getLogger("app.services.scans")


class NoActiveOrganizationsError(ValidationAppError):
    message = "No active organizations are available to scan."

async def start_scan_all(
    session: AsyncSession,
    *,
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
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
            if existing.batch_id is None:
                existing.batch_id = batch.batch_id
            runs.append(existing)
            continue

        run = ScanRun(
            batch_id=batch.batch_id,
            organization_id=org.organization_id,
            trigger="manual",
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
        result = await session.execute(
            select(ScanRun).where(ScanRun.status.in_(("queued", "running")))
        )
        rows = list(result.scalars().all())
        if not rows:
            return
        now = datetime.now(timezone.utc)
        for row in rows:
            row.status = "interrupted"
            row.stage = None
            row.finished_at = now
            row.error_detail = "Server restarted during this scan"
        await session.commit()
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

    semaphore = asyncio.Semaphore(max(1, settings.scan_org_concurrency))

    async def _one(scan_id: uuid.UUID) -> None:
        async with semaphore:
            async with session_factory() as session:
                scan = await session.get(ScanRun, scan_id)
                if scan is None:
                    return
                organization_id = scan.organization_id
            await run_organization_discovery(
                session_factory=session_factory,
                settings=settings,
                llm=llm,
                scan_id=scan_id,
                organization_id=organization_id,
            )

    await asyncio.gather(*[_one(scan_id) for scan_id in scan_ids], return_exceptions=True)
