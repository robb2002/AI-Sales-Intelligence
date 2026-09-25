from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Text, Uuid, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.repositories.base import Base


class Evidence(Base):
    __tablename__ = "evidence"
    __table_args__ = (
        CheckConstraint("char_length(snippet) > 0", name="evidence_snippet_not_empty"),
        CheckConstraint(
            "data_origin IN ('live', 'cached')",
            name="evidence_data_origin_check",
        ),
    )

    evidence_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    signal_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("signals.signal_id", ondelete="CASCADE")
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("documents.document_id", ondelete="CASCADE"), nullable=False
    )
    chunk_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("document_chunks.chunk_id", ondelete="SET NULL")
    )
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("sources.source_id", ondelete="SET NULL")
    )
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    published_on: Mapped[date | None] = mapped_column(Date)
    snippet: Mapped[str] = mapped_column(Text, nullable=False)
    relationship: Mapped[str] = mapped_column(Text, nullable=False)
    data_origin: Mapped[str] = mapped_column(Text, nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


async def create_evidence(
    session: AsyncSession,
    *,
    signal_id: uuid.UUID | None,
    document_id: uuid.UUID,
    source_id: uuid.UUID | None,
    source_url: str,
    published_on: date | None,
    snippet: str,
    relationship: str,
    data_origin: str,
    retrieved_at: datetime,
    chunk_id: uuid.UUID | None = None,
) -> Evidence:
    row = Evidence(
        signal_id=signal_id,
        document_id=document_id,
        chunk_id=chunk_id,
        source_id=source_id,
        source_url=source_url,
        published_on=published_on,
        snippet=snippet,
        relationship=relationship,
        data_origin=data_origin,
        retrieved_at=retrieved_at,
    )
    session.add(row)
    await session.flush()
    return row


async def has_identical_evidence(
    session: AsyncSession,
    *,
    signal_id: uuid.UUID,
    document_id: uuid.UUID,
    snippet: str,
) -> bool:
    value = await session.scalar(
        select(Evidence.evidence_id)
        .where(
            Evidence.signal_id == signal_id,
            Evidence.document_id == document_id,
            Evidence.snippet == snippet,
        )
        .limit(1)
    )
    return value is not None


async def document_has_validated_evidence(
    session: AsyncSession, document_id: uuid.UUID
) -> bool:
    from app.repositories.signals import Signal

    value = await session.scalar(
        select(Evidence.evidence_id)
        .join(Signal, Signal.signal_id == Evidence.signal_id)
        .where(
            Evidence.document_id == document_id,
            Signal.state == "validated",
        )
        .limit(1)
    )
    return value is not None


async def list_for_signal(session: AsyncSession, signal_id: uuid.UUID) -> list[Evidence]:
    rows = await session.execute(
        select(Evidence).where(Evidence.signal_id == signal_id).order_by(Evidence.created_at)
    )
    return list(rows.scalars().all())


async def list_by_ids(
    session: AsyncSession, evidence_ids: list[uuid.UUID]
) -> list[Evidence]:
    if not evidence_ids:
        return []
    rows = await session.execute(
        select(Evidence).where(Evidence.evidence_id.in_(evidence_ids))
    )
    by_id = {row.evidence_id: row for row in rows.scalars().all()}
    return [by_id[eid] for eid in evidence_ids if eid in by_id]


async def count_for_signals(
    session: AsyncSession, signal_ids: list[uuid.UUID]
) -> dict[uuid.UUID, int]:
    if not signal_ids:
        return {}
    rows = await session.execute(
        select(Evidence.signal_id, func.count())
        .where(Evidence.signal_id.in_(signal_ids))
        .group_by(Evidence.signal_id)
    )
    return {row[0]: int(row[1]) for row in rows.all()}
