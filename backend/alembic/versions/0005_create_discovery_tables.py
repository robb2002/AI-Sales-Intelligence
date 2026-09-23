"""create sources, organization_sources, scan_batches, scan_runs

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-23
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sources",
        sa.Column(
            "source_id",
            sa.Uuid(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("source_key", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("official_url", sa.Text(), nullable=False),
        sa.Column("source_kind", sa.Text(), nullable=False),
        sa.Column("reliability_label", sa.Text(), nullable=True),
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
            "source_kind IN ('official_api', 'official_data_file', 'official_website')",
            name="sources_source_kind_check",
        ),
        sa.CheckConstraint(
            "reliability_label IS NULL OR reliability_label IN ('official_api', 'official_website')",
            name="sources_reliability_label_check",
        ),
        sa.UniqueConstraint("source_key", name="sources_source_key_key"),
    )

    op.create_table(
        "organization_sources",
        sa.Column(
            "organization_source_id",
            sa.Uuid(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("source_title", sa.Text(), nullable=True),
        sa.Column("page_category", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("is_official", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("last_validated_at", sa.DateTime(timezone=True), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.organization_id"],
            name="organization_sources_organization_id_fkey",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "page_category IN ("
            "'procurement', 'technology', 'digital_learning', 'assessment', "
            "'funding', 'leadership', 'strategic_initiative', 'partnership'"
            ")",
            name="organization_sources_page_category_check",
        ),
        sa.CheckConstraint(
            "status IN ('approved', 'rejected')",
            name="organization_sources_status_check",
        ),
        sa.CheckConstraint("char_length(url) > 0", name="organization_sources_url_not_empty"),
        sa.UniqueConstraint(
            "organization_id",
            "url",
            name="organization_sources_organization_id_url_key",
        ),
    )
    op.create_index(
        "ix_organization_sources_organization_id",
        "organization_sources",
        ["organization_id"],
    )
    op.create_index("ix_organization_sources_status", "organization_sources", ["status"])

    op.create_table(
        "scan_batches",
        sa.Column(
            "batch_id",
            sa.Uuid(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "scan_runs",
        sa.Column(
            "scan_id",
            sa.Uuid(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("batch_id", sa.Uuid(), nullable=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("trigger", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("stage", sa.Text(), nullable=True),
        sa.Column(
            "sources",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("signals_created", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("signals_updated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("opportunities_created", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("opportunities_updated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("candidates_found", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sources_approved", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sources_rejected", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["batch_id"],
            ["scan_batches.batch_id"],
            name="scan_runs_batch_id_fkey",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.organization_id"],
            name="scan_runs_organization_id_fkey",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "trigger IN ('manual', 'scheduled')",
            name="scan_runs_trigger_check",
        ),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'partial', 'failed', 'interrupted')",
            name="scan_runs_status_check",
        ),
        sa.CheckConstraint(
            "stage IS NULL OR stage IN ("
            "'discovering', 'validating_sources', 'saving_sources', "
            "'collecting', 'extracting', 'validating', 'deduplicating', 'correlating', 'scoring'"
            ")",
            name="scan_runs_stage_check",
        ),
        sa.CheckConstraint("signals_created >= 0", name="scan_runs_signals_created_check"),
        sa.CheckConstraint("signals_updated >= 0", name="scan_runs_signals_updated_check"),
        sa.CheckConstraint(
            "opportunities_created >= 0", name="scan_runs_opportunities_created_check"
        ),
        sa.CheckConstraint(
            "opportunities_updated >= 0", name="scan_runs_opportunities_updated_check"
        ),
        sa.CheckConstraint("candidates_found >= 0", name="scan_runs_candidates_found_check"),
        sa.CheckConstraint("sources_approved >= 0", name="scan_runs_sources_approved_check"),
        sa.CheckConstraint("sources_rejected >= 0", name="scan_runs_sources_rejected_check"),
    )
    op.create_index(
        "ix_scan_runs_organization_started",
        "scan_runs",
        ["organization_id", sa.text("started_at DESC")],
    )
    op.create_index(
        "uq_scan_runs_one_active_per_org",
        "scan_runs",
        ["organization_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('queued', 'running')"),
    )


def downgrade() -> None:
    op.drop_index("uq_scan_runs_one_active_per_org", table_name="scan_runs")
    op.drop_index("ix_scan_runs_organization_started", table_name="scan_runs")
    op.drop_table("scan_runs")
    op.drop_table("scan_batches")
    op.drop_index("ix_organization_sources_status", table_name="organization_sources")
    op.drop_index("ix_organization_sources_organization_id", table_name="organization_sources")
    op.drop_table("organization_sources")
    op.drop_table("sources")
