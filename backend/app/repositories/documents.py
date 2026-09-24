from datetime import date, datetime
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.repositories.base import Base
from app.repositories.organizations import Organization
from app.repositories.sources import Source


class Document(Base):
    __tablename__ = "documents"

    document_id: Mapped[UUID] = mapped_column(
        primary_key=True, server_default=sa.text("gen_random_uuid()")
    )
    source_id: Mapped[UUID] = mapped_column(
        ForeignKey("sources.source_id", ondelete="CASCADE"), nullable=False
    )
    organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organizations.organization_id", ondelete="CASCADE")
    )
    external_id: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str | None] = mapped_column(Text)
    body_text: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(Text, nullable=False)
    published_on: Mapped[date | None] = mapped_column(Date)
    http_status: Mapped[int | None] = mapped_column(Integer)
    data_origin: Mapped[str] = mapped_column(Text, nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    )

    organization: Mapped[Organization | None] = relationship(lazy="noload")
    source: Mapped[Source] = relationship(lazy="noload")
