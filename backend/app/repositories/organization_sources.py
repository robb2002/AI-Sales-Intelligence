import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Text,
    Uuid,
    func,
    select,
    text,
    update,
)
from sqlalchemy.ext.asyncio import AsyncSession
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
    "news",
)
SOURCE_STATUSES = ("approved", "rejected")


class OrganizationSource(Base):
    __tablename__ = "organization_sources"
    __table_args__ = (
        CheckConstraint(
            "page_category IN ("
            "'procurement', 'technology', 'digital_learning', 'assessment', "
            "'funding', 'leadership', 'strategic_initiative', 'partnership', 'news'"
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


async def fresh_source_ids(
    session: AsyncSession, organization_id: uuid.UUID, since: datetime
) -> set[uuid.UUID]:
    """Approved pages already collected (or found unreadable) inside the refresh window.
    They are not fetched again until the window passes."""
    rows = await session.execute(
        select(OrganizationSource.organization_source_id).where(
            OrganizationSource.organization_id == organization_id,
            OrganizationSource.status == "approved",
            OrganizationSource.extraction_status.in_(("extracted", "failed")),
            OrganizationSource.last_validated_at >= since,
        )
    )
    return set(rows.scalars().all())


async def set_extraction_status(
    session: AsyncSession, organization_source_ids: list[uuid.UUID], status: str
) -> None:
    if not organization_source_ids:
        return
    await session.execute(
        update(OrganizationSource)
        .where(OrganizationSource.organization_source_id.in_(organization_source_ids))
        .values(extraction_status=status)
    )


async def reset_interrupted_extractions(
    session: AsyncSession, organization_id: uuid.UUID | None = None
) -> None:
    statement = update(OrganizationSource).where(
        OrganizationSource.extraction_status == "extracting"
    )
    if organization_id is not None:
        statement = statement.where(OrganizationSource.organization_id == organization_id)
    await session.execute(statement.values(extraction_status="pending"))
