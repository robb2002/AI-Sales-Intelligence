from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Text, Uuid, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.repositories.base import Base

SCOPE_TYPES = frozenset({"organization", "opportunity"})


class AdvisorSession(Base):
    __tablename__ = "advisor_sessions"
    __table_args__ = (
        CheckConstraint(
            "scope_type IN ('organization', 'opportunity')",
            name="advisor_sessions_scope_type_check",
        ),
    )

    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    scope_type: Mapped[str] = mapped_column(Text, nullable=False)
    scope_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("organizations.organization_id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


async def create_session(
    session: AsyncSession,
    *,
    scope_type: str,
    scope_id: uuid.UUID,
    organization_id: uuid.UUID,
) -> AdvisorSession:
    row = AdvisorSession(
        scope_type=scope_type,
        scope_id=scope_id,
        organization_id=organization_id,
    )
    session.add(row)
    await session.flush()
    return row


async def get_session(
    session: AsyncSession, session_id: uuid.UUID
) -> AdvisorSession | None:
    return await session.get(AdvisorSession, session_id)


async def touch_session(session: AsyncSession, row: AdvisorSession) -> None:
    from datetime import timezone

    row.updated_at = datetime.now(timezone.utc)
    await session.flush()
