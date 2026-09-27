"""create organization_peer_competitors

Revision ID: 0022
Revises: 0021
Create Date: 2026-09-26
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0022"
down_revision: str | None = "0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "organization_peer_competitors",
        sa.Column(
            "peer_id",
            sa.Uuid(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "organization_id",
            sa.Uuid(),
            sa.ForeignKey("organizations.organization_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("rank", sa.SmallInteger(), nullable=False),
        sa.Column("competitor_name", sa.Text(), nullable=False),
        sa.Column("source_title", sa.Text(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("snippet", sa.Text(), nullable=False),
        sa.Column("search_query", sa.Text(), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("rank BETWEEN 1 AND 5", name="organization_peer_competitors_rank_check"),
        sa.CheckConstraint(
            "length(trim(competitor_name)) > 0 AND length(trim(snippet)) > 0",
            name="organization_peer_competitors_text_check",
        ),
        sa.UniqueConstraint("organization_id", "rank", name="organization_peer_competitors_rank_uq"),
    )


def downgrade() -> None:
    op.drop_table("organization_peer_competitors")
