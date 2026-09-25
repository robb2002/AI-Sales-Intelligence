from datetime import date, datetime
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy import Date, DateTime, ForeignKey, Integer, Text, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.repositories.base import Base
from app.repositories.organizations import Organization
from app.repositories.sources import Source


class Document(Base):
    __tablename__ = "documents"

    document_id: Mapped[UUID] = mapped_column(
        primary_key=True, server_default=sa.text("gen_random_uuid()")
    )
    source_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("sources.source_id", ondelete="CASCADE")
    )
    organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organizations.organization_id", ondelete="CASCADE")
    )
    organization_source_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organization_sources.organization_source_id", ondelete="SET NULL")
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
    source: Mapped[Source | None] = relationship(lazy="noload")


async def save_current_document(
    session: AsyncSession,
    *,
    organization_id: UUID,
    organization_source_id: UUID,
    source_url: str,
    title: str | None,
    body_text: str,
    content_hash: str,
    published_on: date | None,
    http_status: int | None,
    retrieved_at: datetime,
) -> tuple[str, UUID]:
    """Keep one current document per organization and URL.

    Returns `(status, document_id)` where status is `inserted`, `updated`, or `unchanged`.
    """
    existing = await session.scalar(
        select(Document).where(
            Document.organization_id == organization_id,
            Document.source_url == source_url,
            Document.external_id.is_(None),
        )
    )
    if existing is None:
        row = Document(
            source_id=None,
            organization_id=organization_id,
            organization_source_id=organization_source_id,
            source_url=source_url,
            title=title,
            body_text=body_text,
            content_hash=content_hash,
            published_on=published_on,
            http_status=http_status,
            data_origin="live",
            retrieved_at=retrieved_at,
        )
        session.add(row)
        await session.flush()
        return "inserted", row.document_id

    existing.organization_source_id = organization_source_id
    existing.source_id = None
    if existing.content_hash == content_hash:
        return "unchanged", existing.document_id

    existing.title = title
    existing.body_text = body_text
    existing.content_hash = content_hash
    existing.published_on = published_on
    existing.http_status = http_status
    existing.data_origin = "live"
    existing.retrieved_at = retrieved_at
    await session.flush()
    return "updated", existing.document_id


async def save_api_document(
    session: AsyncSession,
    *,
    source_id: UUID,
    organization_id: UUID,
    external_id: str,
    source_url: str,
    title: str | None,
    body_text: str,
    content_hash: str,
    published_on: date | None,
    http_status: int | None,
    retrieved_at: datetime,
) -> tuple[str, UUID]:
    """One current document per registry source and external id.

    Returns `(status, document_id)` where status is `inserted`, `updated`, or `unchanged`.
    """
    existing = await session.scalar(
        select(Document).where(
            Document.source_id == source_id,
            Document.external_id == external_id,
        )
    )
    if existing is None:
        row = Document(
            source_id=source_id,
            organization_id=organization_id,
            organization_source_id=None,
            external_id=external_id,
            source_url=source_url,
            title=title,
            body_text=body_text,
            content_hash=content_hash,
            published_on=published_on,
            http_status=http_status,
            data_origin="live",
            retrieved_at=retrieved_at,
        )
        session.add(row)
        await session.flush()
        return "inserted", row.document_id

    existing.organization_id = organization_id
    if existing.content_hash == content_hash:
        return "unchanged", existing.document_id

    existing.source_url = source_url
    existing.title = title
    existing.body_text = body_text
    existing.content_hash = content_hash
    existing.published_on = published_on
    existing.http_status = http_status
    existing.data_origin = "live"
    existing.retrieved_at = retrieved_at
    await session.flush()
    return "updated", existing.document_id


async def list_for_organization(
    session: AsyncSession, organization_id: UUID
) -> list[Document]:
    rows = await session.execute(
        select(Document)
        .where(Document.organization_id == organization_id)
        .order_by(Document.retrieved_at.desc())
    )
    return list(rows.scalars().all())


async def list_by_ids(session: AsyncSession, document_ids: list[UUID]) -> list[Document]:
    if not document_ids:
        return []
    rows = await session.execute(
        select(Document)
        .where(Document.document_id.in_(document_ids))
        .order_by(Document.retrieved_at.desc())
    )
    return list(rows.scalars().all())


async def count_by_organization_source(
    session: AsyncSession, organization_source_ids: list[UUID]
) -> dict[UUID, int]:
    if not organization_source_ids:
        return {}
    rows = await session.execute(
        select(Document.organization_source_id, func.count())
        .where(Document.organization_source_id.in_(organization_source_ids))
        .group_by(Document.organization_source_id)
    )
    return {row[0]: int(row[1]) for row in rows.all()}
