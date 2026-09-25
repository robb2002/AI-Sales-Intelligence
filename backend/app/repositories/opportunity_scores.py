from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, SmallInteger, Text, Uuid, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.repositories.base import Base
from app.scoring.v1 import ScoreBreakdown


class OpportunityScore(Base):
    __tablename__ = "opportunity_scores"
    __table_args__ = (
        CheckConstraint("value BETWEEN 0 AND 100", name="opportunity_scores_value_check"),
        CheckConstraint(
            "band IN ('high', 'medium', 'low', 'monitor')",
            name="opportunity_scores_band_check",
        ),
        CheckConstraint(
            "explanation_status IN ('ready', 'unavailable')",
            name="opportunity_scores_explanation_status_check",
        ),
    )

    score_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("opportunities.opportunity_id", ondelete="CASCADE")
    )
    value: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    band: Mapped[str] = mapped_column(Text, nullable=False)
    weight_version: Mapped[str] = mapped_column(Text, nullable=False)
    procurement_relevance: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    related_signal_strength: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    assessment_edtech_relevance: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    recency: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    source_reliability: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    explanation_text: Mapped[str | None] = mapped_column(Text)
    explanation_status: Mapped[str] = mapped_column(Text, nullable=False)
    scored_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


async def insert_score(
    session: AsyncSession,
    *,
    opportunity_id: uuid.UUID,
    breakdown: ScoreBreakdown,
    explanation_text: str | None = None,
    explanation_status: str = "unavailable",
) -> OpportunityScore:
    row = OpportunityScore(
        opportunity_id=opportunity_id,
        value=breakdown.value,
        band=breakdown.band,
        weight_version=breakdown.weight_version,
        procurement_relevance=breakdown.procurement_relevance,
        related_signal_strength=breakdown.related_signal_strength,
        assessment_edtech_relevance=breakdown.assessment_edtech_relevance,
        recency=breakdown.recency,
        source_reliability=breakdown.source_reliability,
        explanation_text=explanation_text,
        explanation_status=explanation_status,
    )
    session.add(row)
    await session.flush()
    return row


async def latest_for_opportunity(
    session: AsyncSession, opportunity_id: uuid.UUID
) -> OpportunityScore | None:
    return await session.scalar(
        select(OpportunityScore)
        .where(OpportunityScore.opportunity_id == opportunity_id)
        .order_by(OpportunityScore.scored_at.desc())
        .limit(1)
    )


async def set_explanation(
    session: AsyncSession,
    *,
    score_id: uuid.UUID,
    explanation_text: str,
) -> None:
    row = await session.get(OpportunityScore, score_id)
    if row is None:
        return
    row.explanation_text = explanation_text
    row.explanation_status = "ready"
    await session.flush()
