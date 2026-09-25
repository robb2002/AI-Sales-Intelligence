import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Text, Uuid, func, select, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.repositories.app_users import AppUser
from app.repositories.base import Base
from app.repositories.organizations import Organization


class ScanBatch(Base):
    __tablename__ = "scan_batches"

    batch_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ScanRun(Base):
    __tablename__ = "scan_runs"
    __table_args__ = (
        CheckConstraint(
            "trigger IN ('manual', 'scheduled')",
            name="scan_runs_trigger_check",
        ),
        CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'partial', 'failed', 'interrupted')",
            name="scan_runs_status_check",
        ),
    )

    scan_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    batch_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("scan_batches.batch_id", ondelete="SET NULL")
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.organization_id", ondelete="CASCADE")
    )
    trigger: Mapped[str] = mapped_column(Text)
    requested_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("app_users.user_id", ondelete="SET NULL")
    )
    status: Mapped[str] = mapped_column(Text)
    stage: Mapped[str | None] = mapped_column(Text)
    sources: Mapped[list] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    signals_created: Mapped[int] = mapped_column(Integer, server_default="0")
    signals_updated: Mapped[int] = mapped_column(Integer, server_default="0")
    opportunities_created: Mapped[int] = mapped_column(Integer, server_default="0")
    opportunities_updated: Mapped[int] = mapped_column(Integer, server_default="0")
    candidates_found: Mapped[int] = mapped_column(Integer, server_default="0")
    sources_approved: Mapped[int] = mapped_column(Integer, server_default="0")
    sources_rejected: Mapped[int] = mapped_column(Integer, server_default="0")
    documents_collected: Mapped[int] = mapped_column(Integer, server_default="0")
    error_detail: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


async def list_scan_runs(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID | None,
    statuses: list[str] | None,
    limit: int,
    offset: int,
) -> tuple[list[tuple[ScanRun, str, str | None]], int]:
    """Newest first. Each row carries the organization name and the requester's email."""
    filters = []
    if organization_id is not None:
        filters.append(ScanRun.organization_id == organization_id)
    if statuses:
        filters.append(ScanRun.status.in_(statuses))

    total = await session.scalar(select(func.count()).select_from(ScanRun).where(*filters))
    rows = await session.execute(
        select(ScanRun, Organization.name, AppUser.email)
        .join(Organization, Organization.organization_id == ScanRun.organization_id)
        .outerjoin(AppUser, AppUser.user_id == ScanRun.requested_by_user_id)
        .where(*filters)
        .order_by(func.coalesce(ScanRun.started_at, ScanRun.created_at).desc())
        .limit(limit)
        .offset(offset)
    )
    return [(row[0], row[1], row[2]) for row in rows.all()], int(total or 0)


async def requester_emails(
    session: AsyncSession, user_ids: list[uuid.UUID]
) -> dict[uuid.UUID, str]:
    ids = [user_id for user_id in user_ids if user_id is not None]
    if not ids:
        return {}
    rows = await session.execute(
        select(AppUser.user_id, AppUser.email).where(AppUser.user_id.in_(ids))
    )
    return {row[0]: row[1] for row in rows.all()}
