from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Text, Uuid, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.repositories.base import Base
from app.repositories.opportunity_scores import OpportunityScore
from app.repositories.organizations import Organization


class Opportunity(Base):
    __tablename__ = "opportunities"
    __table_args__ = (
        CheckConstraint("label = 'potential_opportunity'", name="opportunities_label_check"),
        CheckConstraint(
            "data_origin IN ('live', 'cached')",
            name="opportunities_data_origin_check",
        ),
    )

    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.organization_id", ondelete="CASCADE"), unique=True
    )
    label: Mapped[str] = mapped_column(Text, nullable=False, default="potential_opportunity")
    correlation_text: Mapped[str] = mapped_column(Text, nullable=False)
    recommended_action_text: Mapped[str | None] = mapped_column(Text)
    data_origin: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class OpportunitySignal(Base):
    __tablename__ = "opportunity_signals"

    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("opportunities.opportunity_id", ondelete="CASCADE"), primary_key=True
    )
    signal_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("signals.signal_id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


async def get_by_organization(
    session: AsyncSession, organization_id: uuid.UUID
) -> Opportunity | None:
    return await session.scalar(
        select(Opportunity).where(Opportunity.organization_id == organization_id)
    )


async def get_by_id(session: AsyncSession, opportunity_id: uuid.UUID) -> Opportunity | None:
    return await session.get(Opportunity, opportunity_id)


async def upsert_opportunity(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    correlation_text: str,
    data_origin: str,
    recommended_action_text: str | None = None,
) -> Opportunity:
    existing = await get_by_organization(session, organization_id)
    if existing is None:
        row = Opportunity(
            organization_id=organization_id,
            label="potential_opportunity",
            correlation_text=correlation_text,
            recommended_action_text=recommended_action_text,
            data_origin=data_origin,
        )
        session.add(row)
        await session.flush()
        return row
    existing.correlation_text = correlation_text
    existing.recommended_action_text = recommended_action_text
    existing.data_origin = data_origin
    await session.flush()
    return existing


async def replace_opportunity_signals(
    session: AsyncSession, *, opportunity_id: uuid.UUID, signal_ids: list[uuid.UUID]
) -> None:
    existing = (
        await session.execute(
            select(OpportunitySignal).where(OpportunitySignal.opportunity_id == opportunity_id)
        )
    ).scalars().all()
    for row in existing:
        await session.delete(row)
    await session.flush()
    for signal_id in signal_ids:
        session.add(OpportunitySignal(opportunity_id=opportunity_id, signal_id=signal_id))
    await session.flush()


async def list_signal_ids(
    session: AsyncSession, opportunity_id: uuid.UUID
) -> list[uuid.UUID]:
    rows = await session.execute(
        select(OpportunitySignal.signal_id).where(
            OpportunitySignal.opportunity_id == opportunity_id
        )
    )
    return list(rows.scalars().all())


async def opportunity_ids_for_signals(
    session: AsyncSession, signal_ids: list[uuid.UUID]
) -> dict[uuid.UUID, list[uuid.UUID]]:
    if not signal_ids:
        return {}
    rows = await session.execute(
        select(OpportunitySignal.signal_id, OpportunitySignal.opportunity_id).where(
            OpportunitySignal.signal_id.in_(signal_ids)
        )
    )
    out: dict[uuid.UUID, list[uuid.UUID]] = {sid: [] for sid in signal_ids}
    for signal_id, opportunity_id in rows.all():
        out.setdefault(signal_id, []).append(opportunity_id)
    return out


async def signal_count(session: AsyncSession, opportunity_id: uuid.UUID) -> int:
    value = await session.scalar(
        select(func.count())
        .select_from(OpportunitySignal)
        .where(OpportunitySignal.opportunity_id == opportunity_id)
    )
    return int(value or 0)


async def list_opportunities(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID | None,
    organization_types: list[str] | None,
    state_codes: list[str] | None,
    bands: list[str] | None,
    date_from: date | None,
    date_to: date | None,
    sort: str,
    direction: str,
    limit: int,
    offset: int,
) -> tuple[list[tuple[Opportunity, Organization, OpportunityScore | None, int]], int]:
    """Returns (opportunity, organization, latest_score, signal_count) rows."""
    filters = []
    if organization_id is not None:
        filters.append(Opportunity.organization_id == organization_id)
    if organization_types:
        filters.append(Organization.organization_type.in_(organization_types))
    if state_codes:
        filters.append(Organization.state_code.in_(state_codes))
    if date_from is not None:
        filters.append(func.date(Opportunity.updated_at) >= date_from)
    if date_to is not None:
        filters.append(func.date(Opportunity.updated_at) <= date_to)

    # Load opportunities + orgs first, then attach latest scores in Python.
    # Fine for MVP scale (tens of orgs).
    list_q = (
        select(Opportunity, Organization)
        .join(Organization, Organization.organization_id == Opportunity.organization_id)
    )
    count_q = (
        select(func.count())
        .select_from(Opportunity)
        .join(Organization, Organization.organization_id == Opportunity.organization_id)
    )
    for f in filters:
        list_q = list_q.where(f)
        count_q = count_q.where(f)

    pairs = (await session.execute(list_q)).all()
    enriched: list[tuple[Opportunity, Organization, OpportunityScore | None, int]] = []
    for opportunity, organization in pairs:
        score = await session.scalar(
            select(OpportunityScore)
            .where(OpportunityScore.opportunity_id == opportunity.opportunity_id)
            .order_by(OpportunityScore.scored_at.desc())
            .limit(1)
        )
        if bands and (score is None or score.band not in bands):
            continue
        count = await signal_count(session, opportunity.opportunity_id)
        enriched.append((opportunity, organization, score, count))

    reverse = direction != "asc"
    if sort == "updated_at":
        enriched.sort(key=lambda row: row[0].updated_at, reverse=reverse)
    else:
        enriched.sort(
            key=lambda row: (row[2].value if row[2] is not None else -1),
            reverse=reverse,
        )

    total = len(enriched)
    page = enriched[offset : offset + limit]
    return page, total
