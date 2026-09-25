import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Text, Uuid, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.repositories.base import Base


class Source(Base):
    __tablename__ = "sources"
    __table_args__ = (
        CheckConstraint(
            "source_kind IN ('official_api', 'official_data_file', 'official_website')",
            name="sources_source_kind_check",
        ),
        CheckConstraint(
            "reliability_label IS NULL OR reliability_label IN ('official_api', 'official_website')",
            name="sources_reliability_label_check",
        ),
    )

    source_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    source_key: Mapped[str] = mapped_column(Text, unique=True)
    name: Mapped[str] = mapped_column(Text)
    official_url: Mapped[str] = mapped_column(Text)
    source_kind: Mapped[str] = mapped_column(Text)
    reliability_label: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


async def get_by_key(session: AsyncSession, source_key: str) -> Source | None:
    return await session.scalar(select(Source).where(Source.source_key == source_key))
