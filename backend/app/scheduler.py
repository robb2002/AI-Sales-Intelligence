"""Daily Scan All on APScheduler (TECHNICAL_PRD). One process, one worker, no queue.

Off unless SCHEDULER_ENABLED=true. It starts the same Scan All the button starts, with
trigger='scheduled', so the pipeline, budgets and SAM.gov cap are exactly the manual path.
"""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.services import scans as scans_service
from app.services.scans import NoActiveOrganizationsError

logger = logging.getLogger("app.scheduler")

JOB_ID = "daily_scan_all"


def create_scheduler(settings: Settings, session_factory: async_sessionmaker[AsyncSession]):
    """Return a configured (not yet started) scheduler, or None when disabled."""
    if not settings.scheduler_enabled:
        return None

    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger

    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        _run_scan_all,
        CronTrigger(
            hour=settings.scheduler_scan_all_hour_utc,
            minute=settings.scheduler_scan_all_minute,
            timezone="UTC",
        ),
        kwargs={"settings": settings, "session_factory": session_factory},
        id=JOB_ID,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=3600,
        replace_existing=True,
    )
    return scheduler


async def _run_scan_all(
    *, settings: Settings, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    try:
        async with session_factory() as session:
            batch, runs, started = await scans_service.start_scan_all(
                session,
                settings=settings,
                session_factory=session_factory,
                requested_by_user_id=None,
                trigger="scheduled",
            )
        logger.info(
            "Scheduled Scan All started",
            extra={
                "fields": {
                    "batch_id": str(batch.batch_id),
                    "organizations": len(runs),
                    "started": len(started),
                }
            },
        )
    except NoActiveOrganizationsError:
        logger.info("Scheduled Scan All skipped: no active organizations")
    except Exception:
        logger.exception("Scheduled Scan All failed to start")
