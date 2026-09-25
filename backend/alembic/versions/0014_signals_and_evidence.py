"""signals and evidence tables for M5 extraction

Revision ID: 0014
Revises: 0013
Create Date: 2026-09-24
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SIGNAL_TYPES = (
    "procurement",
    "technology_initiative",
    "leadership_change",
    "funding_budget",
    "strategic_announcement",
    "competitor_vendor",
    "contract_renewal",
)
_STATES = ("detected", "validated", "rejected", "merged", "superseded")


def upgrade() -> None:
    op.create_table(
        "signals",
        sa.Column(
            "signal_id",
            sa.Uuid(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("signal_type", sa.Text(), nullable=False),
        sa.Column("state", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("published_on", sa.Date(), nullable=True),
        sa.Column("merged_into_signal_id", sa.Uuid(), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("ai_summary", sa.Text(), nullable=True),
        sa.Column("data_origin", sa.Text(), nullable=False),
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
            name="signals_organization_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["merged_into_signal_id"],
            ["signals.signal_id"],
            name="signals_merged_into_signal_id_fkey",
            ondelete="SET NULL",
        ),
        sa.CheckConstraint(
            "signal_type IN (" + ", ".join(f"'{t}'" for t in _SIGNAL_TYPES) + ")",
            name="signals_signal_type_check",
        ),
        sa.CheckConstraint(
            "state IN (" + ", ".join(f"'{s}'" for s in _STATES) + ")",
            name="signals_state_check",
        ),
        sa.CheckConstraint(
            "data_origin IN ('live', 'cached')",
            name="signals_data_origin_check",
        ),
        sa.CheckConstraint(
            "(state = 'rejected') = (rejection_reason IS NOT NULL)",
            name="signals_rejection_reason_check",
        ),
        sa.CheckConstraint(
            "(state = 'merged') = (merged_into_signal_id IS NOT NULL)",
            name="signals_merged_fk_check",
        ),
        sa.CheckConstraint(
            "merged_into_signal_id IS NULL OR merged_into_signal_id <> signal_id",
            name="signals_merged_not_self_check",
        ),
    )
    op.create_index(
        "ix_signals_org_type_state",
        "signals",
        ["organization_id", "signal_type", "state"],
    )
    op.create_index("ix_signals_org_published", "signals", ["organization_id", "published_on"])
    op.create_index("ix_signals_merged_into", "signals", ["merged_into_signal_id"])

    op.create_table(
        "evidence",
        sa.Column(
            "evidence_id",
            sa.Uuid(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("signal_id", sa.Uuid(), nullable=True),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_id", sa.Uuid(), nullable=True),
        sa.Column("source_id", sa.Uuid(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("published_on", sa.Date(), nullable=True),
        sa.Column("snippet", sa.Text(), nullable=False),
        sa.Column("relationship", sa.Text(), nullable=False),
        sa.Column("data_origin", sa.Text(), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["signal_id"],
            ["signals.signal_id"],
            name="evidence_signal_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.document_id"],
            name="evidence_document_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["sources.source_id"],
            name="evidence_source_id_fkey",
            ondelete="SET NULL",
        ),
        sa.CheckConstraint("char_length(snippet) > 0", name="evidence_snippet_not_empty"),
        sa.CheckConstraint(
            "data_origin IN ('live', 'cached')",
            name="evidence_data_origin_check",
        ),
    )
    op.create_index("ix_evidence_signal_id", "evidence", ["signal_id"])
    op.create_index("ix_evidence_document_id", "evidence", ["document_id"])


def downgrade() -> None:
    op.drop_index("ix_evidence_document_id", table_name="evidence")
    op.drop_index("ix_evidence_signal_id", table_name="evidence")
    op.drop_table("evidence")
    op.drop_index("ix_signals_merged_into", table_name="signals")
    op.drop_index("ix_signals_org_published", table_name="signals")
    op.drop_index("ix_signals_org_type_state", table_name="signals")
    op.drop_table("signals")
