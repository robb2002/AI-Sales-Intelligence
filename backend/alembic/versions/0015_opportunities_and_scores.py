"""opportunities, opportunity_signals, opportunity_scores (M7)

Revision ID: 0015
Revises: 0014
Create Date: 2026-09-24
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "opportunities",
        sa.Column(
            "opportunity_id",
            sa.Uuid(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("label", sa.Text(), nullable=False, server_default="potential_opportunity"),
        sa.Column("correlation_text", sa.Text(), nullable=False),
        sa.Column("recommended_action_text", sa.Text(), nullable=True),
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
            name="opportunities_organization_id_fkey",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("organization_id", name="uq_opportunities_organization_id"),
        sa.CheckConstraint(
            "label = 'potential_opportunity'",
            name="opportunities_label_check",
        ),
        sa.CheckConstraint(
            "data_origin IN ('live', 'cached')",
            name="opportunities_data_origin_check",
        ),
    )

    op.create_table(
        "opportunity_signals",
        sa.Column("opportunity_id", sa.Uuid(), nullable=False),
        sa.Column("signal_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("opportunity_id", "signal_id", name="pk_opportunity_signals"),
        sa.ForeignKeyConstraint(
            ["opportunity_id"],
            ["opportunities.opportunity_id"],
            name="opportunity_signals_opportunity_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["signal_id"],
            ["signals.signal_id"],
            name="opportunity_signals_signal_id_fkey",
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_opportunity_signals_signal_id", "opportunity_signals", ["signal_id"])

    op.create_table(
        "opportunity_scores",
        sa.Column(
            "score_id",
            sa.Uuid(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("opportunity_id", sa.Uuid(), nullable=False),
        sa.Column("value", sa.SmallInteger(), nullable=False),
        sa.Column("band", sa.Text(), nullable=False),
        sa.Column("weight_version", sa.Text(), nullable=False, server_default="v1"),
        sa.Column("procurement_relevance", sa.SmallInteger(), nullable=False),
        sa.Column("related_signal_strength", sa.SmallInteger(), nullable=False),
        sa.Column("assessment_edtech_relevance", sa.SmallInteger(), nullable=False),
        sa.Column("recency", sa.SmallInteger(), nullable=False),
        sa.Column("source_reliability", sa.SmallInteger(), nullable=False),
        sa.Column("explanation_text", sa.Text(), nullable=True),
        sa.Column("explanation_status", sa.Text(), nullable=False, server_default="unavailable"),
        sa.Column(
            "scored_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["opportunity_id"],
            ["opportunities.opportunity_id"],
            name="opportunity_scores_opportunity_id_fkey",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint("value BETWEEN 0 AND 100", name="opportunity_scores_value_check"),
        sa.CheckConstraint(
            "procurement_relevance BETWEEN 0 AND 30",
            name="opportunity_scores_procurement_check",
        ),
        sa.CheckConstraint(
            "related_signal_strength BETWEEN 0 AND 25",
            name="opportunity_scores_related_check",
        ),
        sa.CheckConstraint(
            "assessment_edtech_relevance BETWEEN 0 AND 20",
            name="opportunity_scores_edtech_check",
        ),
        sa.CheckConstraint("recency BETWEEN 0 AND 15", name="opportunity_scores_recency_check"),
        sa.CheckConstraint(
            "source_reliability BETWEEN 0 AND 10",
            name="opportunity_scores_reliability_check",
        ),
        sa.CheckConstraint(
            "value = procurement_relevance + related_signal_strength + "
            "assessment_edtech_relevance + recency + source_reliability",
            name="opportunity_scores_sum_check",
        ),
        sa.CheckConstraint(
            "band IN ('high', 'medium', 'low', 'monitor')",
            name="opportunity_scores_band_check",
        ),
        sa.CheckConstraint(
            "explanation_status IN ('ready', 'unavailable')",
            name="opportunity_scores_explanation_status_check",
        ),
        sa.CheckConstraint(
            "(explanation_status = 'ready') = (explanation_text IS NOT NULL)",
            name="opportunity_scores_explanation_ready_check",
        ),
    )
    op.create_index(
        "ix_opportunity_scores_opportunity_scored",
        "opportunity_scores",
        ["opportunity_id", sa.text("scored_at DESC")],
    )


def downgrade() -> None:
    op.drop_index("ix_opportunity_scores_opportunity_scored", table_name="opportunity_scores")
    op.drop_table("opportunity_scores")
    op.drop_index("ix_opportunity_signals_signal_id", table_name="opportunity_signals")
    op.drop_table("opportunity_signals")
    op.drop_table("opportunities")
