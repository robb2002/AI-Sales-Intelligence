"""create organizations

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-23
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column(
            "organization_id",
            sa.Uuid(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("organization_type", sa.Text(), nullable=False),
        sa.Column("market_role", sa.Text(), nullable=False),
        sa.Column("tracking_status", sa.Text(), nullable=False),
        sa.Column("state_code", sa.String(length=2), nullable=True),
        sa.Column("website_url", sa.Text(), nullable=True),
        sa.Column("ipeds_unit_id", sa.Text(), nullable=True),
        sa.Column("ipeds_collection_year", sa.Text(), nullable=True),
        sa.Column("ipeds_release", sa.Text(), nullable=True),
        sa.Column("ipeds_source_url", sa.Text(), nullable=True),
        sa.Column("ipeds_attributes", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("briefing_text", sa.Text(), nullable=True),
        sa.Column("briefing_status", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "organization_type IN ('university', 'college', 'k12_district', 'public_sector_education')",
            name="organizations_organization_type_check",
        ),
        sa.CheckConstraint(
            "market_role IN ('target', 'competitor')",
            name="organizations_market_role_check",
        ),
        sa.CheckConstraint(
            "tracking_status IN ('active', 'inactive')",
            name="organizations_tracking_status_check",
        ),
        sa.CheckConstraint(
            "ipeds_release IS NULL OR ipeds_release IN ('final', 'provisional')",
            name="organizations_ipeds_release_check",
        ),
        sa.CheckConstraint(
            "briefing_status IS NULL OR briefing_status IN ('ready', 'unavailable')",
            name="organizations_briefing_status_check",
        ),
        sa.UniqueConstraint("website_url", name="organizations_website_url_key"),
        sa.UniqueConstraint("ipeds_unit_id", name="organizations_ipeds_unit_id_key"),
    )
    op.create_index("ix_organizations_organization_type", "organizations", ["organization_type"])
    op.create_index("ix_organizations_market_role", "organizations", ["market_role"])
    op.create_index("ix_organizations_tracking_status", "organizations", ["tracking_status"])
    op.create_index("ix_organizations_state_code", "organizations", ["state_code"])


def downgrade() -> None:
    op.drop_index("ix_organizations_state_code", table_name="organizations")
    op.drop_index("ix_organizations_tracking_status", table_name="organizations")
    op.drop_index("ix_organizations_market_role", table_name="organizations")
    op.drop_index("ix_organizations_organization_type", table_name="organizations")
    op.drop_table("organizations")
