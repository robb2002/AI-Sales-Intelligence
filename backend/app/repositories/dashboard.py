"""Read-only aggregate queries for the dashboard (API_CONTRACT §10). No writes.

The database is a network hop away, so each function answers one whole question in one query
instead of looping per row.
"""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Date, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.repositories.evidence import Evidence
from app.repositories.opportunities import Opportunity, OpportunitySignal
from app.repositories.opportunity_scores import OpportunityScore
from app.repositories.organizations import Organization
from app.repositories.scans import ScanRun
from app.repositories.signals import Signal
from app.repositories.sources import Source


def _signal_date():
    """A signal's date is its stated publication date, else the day we detected it."""
    return func.coalesce(Signal.published_on, cast(Signal.created_at, Date))


async def opportunity_rows(
    session: AsyncSession,
) -> list[tuple[Opportunity, Organization, OpportunityScore | None, int]]:
    """Every opportunity with its organization, latest score, and signal count. One query."""
    latest_scores = (
        select(OpportunityScore)
        .distinct(OpportunityScore.opportunity_id)
        .order_by(OpportunityScore.opportunity_id, OpportunityScore.scored_at.desc())
        .subquery()
    )
    score = aliased(OpportunityScore, latest_scores)
    signal_counts = (
        select(
            OpportunitySignal.opportunity_id.label("opportunity_id"),
            func.count().label("signal_count"),
        )
        .group_by(OpportunitySignal.opportunity_id)
        .subquery()
    )
    rows = await session.execute(
        select(Opportunity, Organization, score, func.coalesce(signal_counts.c.signal_count, 0))
        .join(Organization, Organization.organization_id == Opportunity.organization_id)
        .outerjoin(score, score.opportunity_id == Opportunity.opportunity_id)
        .outerjoin(signal_counts, signal_counts.c.opportunity_id == Opportunity.opportunity_id)
    )
    return [(row[0], row[1], row[2], int(row[3])) for row in rows.all()]


async def validated_counts(
    session: AsyncSession, *, since: date
) -> dict[str, tuple[int, int]]:
    """Per signal type: (validated total, validated since `since`). One query."""
    in_window = _signal_date() >= since
    rows = await session.execute(
        select(Signal.signal_type, func.count(), func.count().filter(in_window))
        .where(Signal.state == "validated")
        .group_by(Signal.signal_type)
    )
    return {signal_type: (int(total), int(recent)) for signal_type, total, recent in rows.all()}


async def validated_counts_per_day(
    session: AsyncSession, *, since: date, until: date
) -> dict[date, int]:
    day = _signal_date()
    rows = await session.execute(
        select(day, func.count())
        .where(Signal.state == "validated", day >= since, day <= until)
        .group_by(day)
    )
    return {row[0]: int(row[1]) for row in rows.all()}


async def recent_validated_signals(
    session: AsyncSession, *, limit: int
) -> list[tuple[Signal, str]]:
    """Newest validated signals with their organization name. One query."""
    rows = await session.execute(
        select(Signal, Organization.name)
        .join(Organization, Organization.organization_id == Signal.organization_id)
        .where(Signal.state == "validated")
        .order_by(_signal_date().desc(), Signal.created_at.desc())
        .limit(limit)
    )
    return [(row[0], row[1]) for row in rows.all()]


async def recent_scan_runs(session: AsyncSession, *, limit: int = 200) -> list[ScanRun]:
    rows = await session.execute(
        select(ScanRun)
        .order_by(func.coalesce(ScanRun.started_at, ScanRun.created_at).desc())
        .limit(limit)
    )
    return list(rows.scalars().all())


async def evidence_for_opportunities(
    session: AsyncSession, opportunity_ids: list[uuid.UUID]
) -> list[tuple[uuid.UUID, Evidence, str | None]]:
    """(opportunity_id, evidence, source name or None) for the signals behind each opportunity."""
    if not opportunity_ids:
        return []
    rows = await session.execute(
        select(OpportunitySignal.opportunity_id, Evidence, Source.name)
        .join(Evidence, Evidence.signal_id == OpportunitySignal.signal_id)
        .outerjoin(Source, Source.source_id == Evidence.source_id)
        .where(OpportunitySignal.opportunity_id.in_(opportunity_ids))
        .order_by(Evidence.created_at)
    )
    return [(row[0], row[1], row[2]) for row in rows.all()]
