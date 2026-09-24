"""add extraction_status to organization_sources

Revision ID: 0008
Revises: 0007
Create Date: 2026-09-23
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "organization_sources",
        sa.Column(
            "extraction_status",
            sa.Text(),
            nullable=False,
            server_default="pending",
        ),
    )
    op.create_check_constraint(
        "organization_sources_extraction_status_check",
        "organization_sources",
        "extraction_status IN ('pending', 'extracting', 'extracted', 'failed')",
    )


def downgrade() -> None:
    op.drop_constraint("organization_sources_extraction_status_check", "organization_sources")
    op.drop_column("organization_sources", "extraction_status")
