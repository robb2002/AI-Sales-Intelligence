"""Saved top-5 peer competitors per organization (DATABASE_DESIGN §5c)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    SmallInteger,
    Text,
    UniqueConstraint,
    Uuid,
    delete,
    func,
    select,
    text,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.repositories.base import Base


class OrganizationPeerCompetitor(Base):
    __tablename__ = "organization_peer_competitors"
    __table_args__ = (
        CheckConstraint("rank BETWEEN 1 AND 5", name="organization_peer_competitors_rank_check"),
        CheckConstraint(
            "length(trim(competitor_name)) > 0 AND length(trim(snippet)) > 0",
            name="organization_peer_competitors_text_check",
        ),
        UniqueConstraint("organization_id", "rank", name="organization_peer_competitors_rank_uq"),
    )

    peer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.organization_id", ondelete="CASCADE"), nullable=False
    )
    rank: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    competitor_name: Mapped[str] = mapped_column(Text, nullable=False)
    source_title: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    snippet: Mapped[str] = mapped_column(Text, nullable=False)
    search_query: Mapped[str] = mapped_column(Text, nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


async def list_for_organization(
    session: AsyncSession, organization_id: uuid.UUID
) -> list[OrganizationPeerCompetitor]:
    rows = await session.execute(
        select(OrganizationPeerCompetitor)
        .where(OrganizationPeerCompetitor.organization_id == organization_id)
        .order_by(OrganizationPeerCompetitor.rank)
    )
    return list(rows.scalars().all())


async def replace_for_organization(
    session: AsyncSession,
    organization_id: uuid.UUID,
    rows: list[OrganizationPeerCompetitor],
) -> None:
    """Swap the whole set. The caller commits, so a failure keeps the previous list."""
    await session.execute(
        delete(OrganizationPeerCompetitor).where(
            OrganizationPeerCompetitor.organization_id == organization_id
        )
    )
    session.add_all(rows)
    await session.flush()
