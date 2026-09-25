from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Text,
    Uuid,
    func,
    select,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.repositories.base import Base

ADVISOR_KINDS = frozenset({"advisor_user", "advisor_answer"})
ADVISOR_STATUSES = frozenset(
    {"answered", "insufficient_evidence", "out_of_scope", "unavailable"}
)


class AiInteraction(Base):
    __tablename__ = "ai_interactions"
    __table_args__ = (
        CheckConstraint(
            "kind IN ("
            "'score_explanation', 'correlation', 'recommendation', "
            "'org_briefing', 'competitor_briefing', "
            "'advisor_user', 'advisor_answer'"
            ")",
            name="ai_interactions_kind_check",
        ),
        CheckConstraint(
            "advisor_status IS NULL OR advisor_status IN ("
            "'answered', 'insufficient_evidence', 'out_of_scope', 'unavailable'"
            ")",
            name="ai_interactions_advisor_status_check",
        ),
        CheckConstraint(
            "content_layer IS NULL OR content_layer IN ("
            "'fact', 'interpretation', 'potential_opportunity', 'recommended_action'"
            ")",
            name="ai_interactions_content_layer_check",
        ),
    )

    ai_interaction_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("advisor_sessions.session_id", ondelete="CASCADE")
    )
    scan_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("scan_runs.scan_id", ondelete="SET NULL")
    )
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("organizations.organization_id", ondelete="CASCADE")
    )
    opportunity_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("opportunities.opportunity_id", ondelete="CASCADE")
    )
    score_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("opportunity_scores.score_id", ondelete="SET NULL")
    )
    prompt_id: Mapped[str | None] = mapped_column(Text)
    prompt_version: Mapped[str | None] = mapped_column(Text)
    advisor_status: Mapped[str | None] = mapped_column(Text)
    body_text: Mapped[str] = mapped_column(Text, nullable=False)
    content_layer: Mapped[str | None] = mapped_column(Text)
    evidence_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(Uuid), nullable=False, server_default=text("'{}'::uuid[]")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


async def create_interaction(
    session: AsyncSession,
    *,
    kind: str,
    body_text: str,
    session_id: uuid.UUID | None = None,
    organization_id: uuid.UUID | None = None,
    opportunity_id: uuid.UUID | None = None,
    prompt_id: str | None = None,
    prompt_version: str | None = None,
    advisor_status: str | None = None,
    content_layer: str | None = None,
    evidence_ids: list[uuid.UUID] | None = None,
) -> AiInteraction:
    row = AiInteraction(
        kind=kind,
        session_id=session_id,
        organization_id=organization_id,
        opportunity_id=opportunity_id,
        prompt_id=prompt_id,
        prompt_version=prompt_version,
        advisor_status=advisor_status,
        body_text=body_text,
        content_layer=content_layer,
        evidence_ids=evidence_ids or [],
    )
    session.add(row)
    await session.flush()
    return row


async def list_session_turns(
    session: AsyncSession,
    session_id: uuid.UUID,
    *,
    limit: int = 8,
) -> list[AiInteraction]:
    """Latest advisor turns for a session, oldest first (at most 4 user + 4 advisor)."""
    stmt = (
        select(AiInteraction)
        .where(
            AiInteraction.session_id == session_id,
            AiInteraction.kind.in_(("advisor_user", "advisor_answer")),
        )
        .order_by(AiInteraction.created_at.desc())
        .limit(limit)
    )
    rows = list((await session.execute(stmt)).scalars().all())
    rows.reverse()
    return rows
