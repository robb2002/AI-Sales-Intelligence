import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Text, Uuid, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.repositories.base import Base


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
    error_detail: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
