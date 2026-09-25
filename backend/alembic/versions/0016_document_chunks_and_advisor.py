"""document_chunks (pgvector 1536), advisor_sessions, ai_interactions (M11)

Revision ID: 0016
Revises: 0015
Create Date: 2026-09-25
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "document_chunks",
        sa.Column(
            "chunk_id",
            sa.Uuid(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("signal_id", sa.Uuid(), nullable=True),
        sa.Column("source_name", sa.Text(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("published_on", sa.Date(), nullable=True),
        sa.Column("content_role", sa.Text(), nullable=False),
        sa.Column("data_origin", sa.Text(), nullable=False),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("embedding_model", sa.Text(), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["document_id"], ["documents.document_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.organization_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["signal_id"], ["signals.signal_id"], ondelete="SET NULL"
        ),
        sa.CheckConstraint(
            "content_role IN ('signal_source', 'reference')",
            name="document_chunks_content_role_check",
        ),
        sa.CheckConstraint(
            "data_origin IN ('live', 'cached')",
            name="document_chunks_data_origin_check",
        ),
        sa.CheckConstraint(
            "char_length(chunk_text) > 0",
            name="document_chunks_chunk_text_not_empty",
        ),
        sa.UniqueConstraint(
            "document_id", "chunk_index", name="document_chunks_document_index_uq"
        ),
    )
    op.execute("ALTER TABLE document_chunks ADD COLUMN embedding vector(1536)")
    op.execute(
        """
        ALTER TABLE document_chunks ADD CONSTRAINT document_chunks_embedding_pair_check
        CHECK (
          (embedding IS NULL AND embedding_model IS NULL) OR
          (embedding IS NOT NULL AND embedding_model IS NOT NULL)
        )
        """
    )
    op.create_index(
        "ix_document_chunks_organization_id",
        "document_chunks",
        ["organization_id"],
    )
    op.create_index(
        "ix_document_chunks_signal_id",
        "document_chunks",
        ["signal_id"],
    )

    op.create_table(
        "advisor_sessions",
        sa.Column(
            "session_id",
            sa.Uuid(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("scope_type", sa.Text(), nullable=False),
        sa.Column("scope_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
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
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "scope_type IN ('organization', 'opportunity')",
            name="advisor_sessions_scope_type_check",
        ),
    )
    op.create_index(
        "ix_advisor_sessions_organization_id",
        "advisor_sessions",
        ["organization_id"],
    )

    op.create_table(
        "ai_interactions",
        sa.Column(
            "ai_interaction_id",
            sa.Uuid(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=True),
        sa.Column("scan_id", sa.Uuid(), nullable=True),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("opportunity_id", sa.Uuid(), nullable=True),
        sa.Column("score_id", sa.Uuid(), nullable=True),
        sa.Column("prompt_id", sa.Text(), nullable=True),
        sa.Column("prompt_version", sa.Text(), nullable=True),
        sa.Column("advisor_status", sa.Text(), nullable=True),
        sa.Column("body_text", sa.Text(), nullable=False),
        sa.Column("content_layer", sa.Text(), nullable=True),
        sa.Column(
            "evidence_ids",
            sa.ARRAY(sa.Uuid()),
            nullable=False,
            server_default=sa.text("'{}'::uuid[]"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["session_id"], ["advisor_sessions.session_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["scan_id"], ["scan_runs.scan_id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.organization_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["opportunity_id"],
            ["opportunities.opportunity_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["score_id"],
            ["opportunity_scores.score_id"],
            ondelete="SET NULL",
        ),
        sa.CheckConstraint(
            "kind IN ("
            "'score_explanation', 'correlation', 'recommendation', "
            "'org_briefing', 'competitor_briefing', "
            "'advisor_user', 'advisor_answer'"
            ")",
            name="ai_interactions_kind_check",
        ),
        sa.CheckConstraint(
            "advisor_status IS NULL OR advisor_status IN ("
            "'answered', 'insufficient_evidence', 'out_of_scope', 'unavailable'"
            ")",
            name="ai_interactions_advisor_status_check",
        ),
        sa.CheckConstraint(
            "content_layer IS NULL OR content_layer IN ("
            "'fact', 'interpretation', 'potential_opportunity', 'recommended_action'"
            ")",
            name="ai_interactions_content_layer_check",
        ),
    )
    op.create_index(
        "ix_ai_interactions_session_created",
        "ai_interactions",
        ["session_id", "created_at"],
    )
    op.create_index(
        "ix_ai_interactions_opportunity_kind",
        "ai_interactions",
        ["opportunity_id", "kind", "created_at"],
    )
    op.create_index(
        "ix_ai_interactions_organization_kind",
        "ai_interactions",
        ["organization_id", "kind", "created_at"],
    )

    op.create_foreign_key(
        "evidence_chunk_id_fkey",
        "evidence",
        "document_chunks",
        ["chunk_id"],
        ["chunk_id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("evidence_chunk_id_fkey", "evidence", type_="foreignkey")
    op.drop_index("ix_ai_interactions_organization_kind", table_name="ai_interactions")
    op.drop_index("ix_ai_interactions_opportunity_kind", table_name="ai_interactions")
    op.drop_index("ix_ai_interactions_session_created", table_name="ai_interactions")
    op.drop_table("ai_interactions")
    op.drop_index("ix_advisor_sessions_organization_id", table_name="advisor_sessions")
    op.drop_table("advisor_sessions")
    op.drop_index("ix_document_chunks_signal_id", table_name="document_chunks")
    op.drop_index("ix_document_chunks_organization_id", table_name="document_chunks")
    op.drop_table("document_chunks")
