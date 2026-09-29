"""Manager-set, one-time scheduled scan triggers: per-organization and portfolio-wide (Scan All).

A manager picks a future UTC date/time — either on one organization (Edit organization >
Schedule tab, `organizations.scheduled_scan_at`) or for Scan All (Organizations page > Scheduler
button, the `scan_all_trigger` singleton row). This checker runs both on an interval, starts the
matching scan(s) once each time arrives, and clears the field so each fires exactly once.

Always on — independent of `app/scheduler.py`'s daily Scan All job and its SCHEDULER_ENABLED
toggle, which is off by default and unrelated to these manager-facing, UI-set schedules. Does not
change that module or its behavior.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.core.errors import AppError
from app.repositories import scan_all_trigger as scan_all_trigger_repo
from app.repositories.organizations import list_due_scheduled_scans
from app.services import scans as scans_service
from app.services.scans import NoActiveOrganizationsError

logger = logging.getLogger("app.scheduled_scan_trigger")

JOB_ID = "organization_scheduled_scan_trigger"
SCAN_ALL_JOB_ID = "scan_all_scheduled_trigger"
CHECK_INTERVAL_SECONDS = 60


def create_scheduled_scan_checker(
    settings: Settings, session_factory: async_sessionmaker[AsyncSession]
):
    """Return a configured (not yet started) scheduler. Always created; caller starts it."""
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.interval import IntervalTrigger

    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        _check_due_organizations,
        IntervalTrigger(seconds=CHECK_INTERVAL_SECONDS),
        kwargs={"settings": settings, "session_factory": session_factory},
        id=JOB_ID,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=CHECK_INTERVAL_SECONDS - 5,
        replace_existing=True,
    )
    scheduler.add_job(
        _check_due_scan_all,
        IntervalTrigger(seconds=CHECK_INTERVAL_SECONDS),
        kwargs={"settings": settings, "session_factory": session_factory},
        id=SCAN_ALL_JOB_ID,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=CHECK_INTERVAL_SECONDS - 5,
        replace_existing=True,
    )
    return scheduler


async def _check_due_scan_all(
    *, settings: Settings, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    now = datetime.now(timezone.utc)
    async with session_factory() as session:
        row = await scan_all_trigger_repo.get_trigger(session)
        if row.scheduled_at is None or row.scheduled_at > now:
            return
        row.scheduled_at = None
        await session.commit()

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
            "Scheduled Scan All started (manager-set trigger)",
            extra={
                "fields": {
                    "batch_id": str(batch.batch_id),
                    "organizations": len(runs),
                    "started": len(started),
                }
            },
        )
    except NoActiveOrganizationsError:
        logger.info("Scheduled Scan All (manager-set trigger) skipped: no active organizations")
    except Exception:
        logger.exception("Scheduled Scan All (manager-set trigger) failed to start")


async def _check_due_organizations(
    *, settings: Settings, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    now = datetime.now(timezone.utc)
    async with session_factory() as session:
        due = await list_due_scheduled_scans(session, now=now)
        if not due:
            return
        due_ids = [org.organization_id for org in due]
        # Clear first, in the same transaction, so a slow scan start can't cause a re-trigger
        # on the next interval tick.
        for org in due:
            org.scheduled_scan_at = None
        await session.commit()

    for organization_id in due_ids:
        try:
            async with session_factory() as session:
                _run, _org, joined_existing = await scans_service.start_scan_for_organization(
                    session,
                    organization_id,
                    settings=settings,
                    session_factory=session_factory,
                    requested_by_user_id=None,
                    trigger="scheduled",
                )
            logger.info(
                "Scheduled organization scan started",
                extra={
                    "fields": {
                        "organization_id": str(organization_id),
                        "joined_existing": joined_existing,
                    }
                },
            )
        except AppError as exc:
            # Organization went inactive, was deleted, or was mid-scan between the fetch above
            # and now. The schedule is already cleared; log and move on to the next one.
            logger.info(
                "Scheduled organization scan skipped",
                extra={"fields": {"organization_id": str(organization_id), "reason": exc.code}},
            )
        except Exception:
            logger.exception(
                "Scheduled organization scan failed to start",
                extra={"fields": {"organization_id": str(organization_id)}},
            )
