import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Text, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.repositories.base import Base

PAGE_CATEGORIES = (
    "procurement",
    "technology",
    "digital_learning",
    "assessment",
    "funding",
    "leadership",
    "strategic_initiative",
    "partnership",
)
SOURCE_STATUSES = ("approved", "rejected")


class OrganizationSource(Base):
    __tablename__ = "organization_sources"
    __table_args__ = (
        CheckConstraint(
            "page_category IN ("
            "'procurement', 'technology', 'digital_learning', 'assessment', "
            "'funding', 'leadership', 'strategic_initiative', 'partnership'"
            ")",
            name="organization_sources_page_category_check",
        ),
        CheckConstraint(
            "status IN ('approved', 'rejected')",
            name="organization_sources_status_check",
        ),
    )

    organization_source_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.organization_id", ondelete="CASCADE"), index=True
    )
    url: Mapped[str] = mapped_column(Text)
    source_title: Mapped[str | None] = mapped_column(Text)
    page_category: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, index=True)
    extraction_status: Mapped[str] = mapped_column(Text, server_default=text("'pending'"))
    is_official: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    last_validated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
