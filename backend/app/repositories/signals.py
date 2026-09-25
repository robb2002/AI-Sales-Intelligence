from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Text, Uuid, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.repositories.base import Base

SIGNAL_TYPES = (
    "procurement",
    "technology_initiative",
    "leadership_change",
    "funding_budget",
    "strategic_announcement",
    "competitor_vendor",
    "contract_renewal",
)
SIGNAL_STATES = ("detected", "validated", "rejected", "merged", "superseded")


class Signal(Base):
    __tablename__ = "signals"
    __table_args__ = (
        CheckConstraint(
            "signal_type IN (" + ", ".join(f"'{t}'" for t in SIGNAL_TYPES) + ")",
            name="signals_signal_type_check",
        ),
        CheckConstraint(
            "state IN (" + ", ".join(f"'{s}'" for s in SIGNAL_STATES) + ")",
            name="signals_state_check",
        ),
        CheckConstraint(
            "data_origin IN ('live', 'cached')",
            name="signals_data_origin_check",
        ),
    )

    signal_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.organization_id", ondelete="CASCADE"), nullable=False
    )
    signal_type: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    published_on: Mapped[date | None] = mapped_column(Date)
    merged_into_signal_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("signals.signal_id", ondelete="SET NULL")
    )
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    ai_summary: Mapped[str | None] = mapped_column(Text)
    data_origin: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


async def create_signal(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    signal_type: str,
    state: str,
    title: str,
    summary: str,
    published_on: date | None,
    rejection_reason: str | None,
    ai_summary: str | None,
    data_origin: str,
    merged_into_signal_id: uuid.UUID | None = None,
) -> Signal:
    row = Signal(
        organization_id=organization_id,
        signal_type=signal_type,
        state=state,
        title=title,
        summary=summary,
        published_on=published_on,
        rejection_reason=rejection_reason,
        ai_summary=ai_summary,
        data_origin=data_origin,
        merged_into_signal_id=merged_into_signal_id,
    )
    session.add(row)
    await session.flush()
    return row


async def find_validated_by_external_id(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    signal_type: str,
    external_id: str,
) -> Signal | None:
    """Dedup tier 2: same org, type, and source external id via evidence→document."""
    from app.repositories.documents import Document
    from app.repositories.evidence import Evidence

    return await session.scalar(
        select(Signal)
        .join(Evidence, Evidence.signal_id == Signal.signal_id)
        .join(Document, Document.document_id == Evidence.document_id)
        .where(
            Signal.organization_id == organization_id,
            Signal.signal_type == signal_type,
            Signal.state == "validated",
            Document.external_id == external_id,
        )
        .order_by(Signal.created_at.asc())
        .limit(1)
    )


async def find_validated_by_document_type(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    signal_type: str,
    document_id: uuid.UUID,
    title_normalized: str,
) -> Signal | None:
    """Same page + type + normalized title → treat as the same event."""
    from app.repositories.evidence import Evidence

    if not title_normalized:
        return None
    rows = (
        await session.execute(
            select(Signal)
            .join(Evidence, Evidence.signal_id == Signal.signal_id)
            .where(
                Signal.organization_id == organization_id,
                Signal.signal_type == signal_type,
                Signal.state == "validated",
                Evidence.document_id == document_id,
            )
            .order_by(Signal.created_at.asc())
        )
    ).scalars().all()
    for row in rows:
        if _normalize_title(row.title) == title_normalized:
            return row
    return None


async def find_validated_by_snippet(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    signal_type: str,
    snippet: str,
) -> Signal | None:
    from app.repositories.evidence import Evidence

    if not snippet:
        return None
    return await session.scalar(
        select(Signal)
        .join(Evidence, Evidence.signal_id == Signal.signal_id)
        .where(
            Signal.organization_id == organization_id,
            Signal.signal_type == signal_type,
            Signal.state == "validated",
            Evidence.snippet == snippet,
        )
        .order_by(Signal.created_at.asc())
        .limit(1)
    )


async def find_validated_by_title_in_window(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    signal_type: str,
    title_normalized: str,
    published_on: date | None,
    window_days: int,
) -> Signal | None:
    if not title_normalized:
        return None
    rows = (
        await session.execute(
            select(Signal)
            .where(
                Signal.organization_id == organization_id,
                Signal.signal_type == signal_type,
                Signal.state == "validated",
            )
            .order_by(Signal.created_at.asc())
        )
    ).scalars().all()
    for row in rows:
        if _normalize_title(row.title) != title_normalized:
            continue
        if _dates_within_window(row.published_on, published_on, window_days):
            return row
    return None


async def list_validated_for_organization(
    session: AsyncSession, organization_id: uuid.UUID
) -> list[Signal]:
    rows = await session.execute(
        select(Signal)
        .where(
            Signal.organization_id == organization_id,
            Signal.state == "validated",
        )
        .order_by(Signal.created_at.asc())
    )
    return list(rows.scalars().all())


def _normalize_title(value: str) -> str:
    import re

    text = value.lower().strip()
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _dates_within_window(a: date | None, b: date | None, days: int) -> bool:
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return abs((a - b).days) <= days


async def list_signals(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID | None,
    signal_types: list[str] | None,
    states: list[str] | None,
    q: str | None,
    limit: int,
    offset: int,
) -> tuple[list[Signal], int]:
    from sqlalchemy import func as sa_func

    filters = []
    if organization_id is not None:
        filters.append(Signal.organization_id == organization_id)
    if signal_types:
        filters.append(Signal.signal_type.in_(signal_types))
    if states:
        filters.append(Signal.state.in_(states))
    else:
        filters.append(Signal.state == "validated")
    if q and q.strip():
        pattern = f"%{q.strip()}%"
        filters.append((Signal.title.ilike(pattern)) | (Signal.summary.ilike(pattern)))

    count_q = select(sa_func.count()).select_from(Signal)
    list_q = select(Signal)
    for f in filters:
        count_q = count_q.where(f)
        list_q = list_q.where(f)

    total = int(await session.scalar(count_q) or 0)
    rows = (
        await session.execute(
            list_q.order_by(
                Signal.published_on.desc().nullslast(),
                Signal.created_at.desc(),
            ).limit(limit).offset(offset)
        )
    ).scalars().all()
    return list(rows), total
