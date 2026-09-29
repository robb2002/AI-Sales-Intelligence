"""Singleton row holding the manager-set, one-time future UTC trigger for Scan All.

Mirrors `organizations.scheduled_scan_at` (0023) at portfolio scope instead of per-organization.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, SmallInteger, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.repositories.base import Base

ROW_ID = 1


class ScanAllTrigger(Base):
    __tablename__ = "scan_all_trigger"
    __table_args__ = (CheckConstraint("id = 1", name="scan_all_trigger_singleton_check"),)

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


async def get_trigger(session: AsyncSession) -> ScanAllTrigger:
    """The single row, seeded by migration 0024. session.get returning None would mean the
    seed row is missing — that is a deployment error, not something to paper over here."""
    row = await session.get(ScanAllTrigger, ROW_ID)
    if row is None:
        raise RuntimeError("scan_all_trigger seed row (id=1) is missing; re-run migrations")
    return row
