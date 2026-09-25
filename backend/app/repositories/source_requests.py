"""Count outbound registry API calls for application rate limits."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import DateTime, Integer, Text, Uuid, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.repositories.base import Base


class SourceRequestLog(Base):
    __tablename__ = "source_request_log"

    request_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    source_key: Mapped[str] = mapped_column(Text, nullable=False)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    http_status: Mapped[int | None] = mapped_column(Integer)
    outcome: Mapped[str] = mapped_column(Text, nullable=False)
    detail: Mapped[str | None] = mapped_column(Text)


async def count_recent(
    session: AsyncSession, *, source_key: str, within_hours: int = 24
) -> int:
    since = datetime.now(timezone.utc) - timedelta(hours=within_hours)
    value = await session.scalar(
        select(func.count())
        .select_from(SourceRequestLog)
        .where(
            SourceRequestLog.source_key == source_key,
            SourceRequestLog.requested_at >= since,
            SourceRequestLog.outcome.in_(("ok", "error", "rejected")),
        )
    )
    return int(value or 0)


async def record(
    session: AsyncSession,
    *,
    source_key: str,
    outcome: str,
    http_status: int | None = None,
    detail: str | None = None,
) -> None:
    session.add(
        SourceRequestLog(
            source_key=source_key,
            outcome=outcome,
            http_status=http_status,
            detail=detail,
        )
    )
    await session.flush()
