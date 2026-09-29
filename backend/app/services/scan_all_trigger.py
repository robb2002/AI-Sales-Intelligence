"""Manager-set, one-time future Scan All trigger (portfolio scope). Read/write only; the
always-on checker that fires it lives in app/scheduled_scan_trigger.py."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import scan_all_trigger as repo
from app.schemas.scan_all_trigger import ScanAllTriggerResponse


async def get_schedule(session: AsyncSession) -> ScanAllTriggerResponse:
    row = await repo.get_trigger(session)
    return ScanAllTriggerResponse(scheduled_at=row.scheduled_at)


async def set_schedule(
    session: AsyncSession, scheduled_at: datetime | None
) -> ScanAllTriggerResponse:
    row = await repo.get_trigger(session)
    row.scheduled_at = scheduled_at
    await session.commit()
    return ScanAllTriggerResponse(scheduled_at=row.scheduled_at)
