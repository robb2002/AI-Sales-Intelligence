import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, String, Text, Uuid, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.repositories.base import Base

ORGANIZATION_TYPES = ("university", "college", "k12_district", "public_sector_education")
MARKET_ROLES = ("target", "competitor")
TRACKING_STATUSES = ("active", "inactive")


class Organization(Base):
    __tablename__ = "organizations"
    __table_args__ = (
        CheckConstraint(
            "organization_type IN ('university', 'college', 'k12_district', 'public_sector_education')",
            name="organizations_organization_type_check",
        ),
        CheckConstraint(
            "market_role IN ('target', 'competitor')",
            name="organizations_market_role_check",
        ),
        CheckConstraint(
            "tracking_status IN ('active', 'inactive')",
            name="organizations_tracking_status_check",
        ),
        CheckConstraint(
            "ipeds_release IS NULL OR ipeds_release IN ('final', 'provisional')",
            name="organizations_ipeds_release_check",
        ),
        CheckConstraint(
            "briefing_status IS NULL OR briefing_status IN ('ready', 'unavailable')",
            name="organizations_briefing_status_check",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(Text)
    organization_type: Mapped[str] = mapped_column(Text)
    market_role: Mapped[str] = mapped_column(Text)
    tracking_status: Mapped[str] = mapped_column(Text)
    state_code: Mapped[str | None] = mapped_column(String(2))
    website_url: Mapped[str | None] = mapped_column(Text, unique=True)
    ipeds_unit_id: Mapped[str | None] = mapped_column(Text, unique=True)
    ipeds_collection_year: Mapped[str | None] = mapped_column(Text)
    ipeds_release: Mapped[str | None] = mapped_column(Text)
    ipeds_source_url: Mapped[str | None] = mapped_column(Text)
    ipeds_attributes: Mapped[object | None] = mapped_column(JSONB)
    briefing_text: Mapped[str | None] = mapped_column(Text)
    briefing_status: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
