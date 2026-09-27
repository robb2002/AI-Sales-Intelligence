"""Read-only queries for competitive intelligence (API_CONTRACT §10a). No writes."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.evidence import Evidence
from app.repositories.organizations import Organization
from app.repositories.scans import ScanRun
from app.repositories.signals import Signal
from app.repositories.sources import Source


async def competitor_organizations(session: AsyncSession) -> list[Organization]:
    rows = await session.execute(
        select(Organization)
        .where(Organization.market_role == "competitor")
        .order_by(Organization.name)
    )
    return list(rows.scalars().all())


async def last_finished_scans(
    session: AsyncSession, organization_ids: list[uuid.UUID]
) -> dict[uuid.UUID, datetime]:
    if not organization_ids:
        return {}
    rows = await session.execute(
        select(ScanRun.organization_id, func.max(ScanRun.finished_at))
        .where(ScanRun.organization_id.in_(organization_ids), ScanRun.finished_at.is_not(None))
        .group_by(ScanRun.organization_id)
    )
    return {org_id: finished for org_id, finished in rows.all()}


async def validated_signals(
    session: AsyncSession, organization_ids: list[uuid.UUID]
) -> list[Signal]:
    """Validated competitor_vendor signals of the given competitors, newest first."""
    if not organization_ids:
        return []
    rows = await session.execute(
        select(Signal)
        .where(
            Signal.organization_id.in_(organization_ids),
            Signal.signal_type == "competitor_vendor",
            Signal.state == "validated",
        )
        .order_by(Signal.published_on.desc().nullslast(), Signal.created_at.desc())
    )
    return list(rows.scalars().all())


async def evidence_for_signals(
    session: AsyncSession, signal_ids: list[uuid.UUID]
) -> list[tuple[Evidence, str | None]]:
    if not signal_ids:
        return []
    rows = await session.execute(
        select(Evidence, Source.name)
        .outerjoin(Source, Source.source_id == Evidence.source_id)
        .where(Evidence.signal_id.in_(signal_ids))
        .order_by(Evidence.created_at)
    )
    return [(row[0], row[1]) for row in rows.all()]
