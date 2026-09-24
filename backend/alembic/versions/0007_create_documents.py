"""create documents table

Revision ID: 0007
Revises: 0006
Create Date: 2026-09-23
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column(
            "document_id",
            sa.Uuid(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("external_id", sa.Text(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("body_text", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.Text(), nullable=False),
        sa.Column("published_on", sa.Date(), nullable=True),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("data_origin", sa.Text(), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["sources.source_id"],
            name="documents_source_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.organization_id"],
            name="documents_organization_id_fkey",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "data_origin IN ('live', 'cached')",
            name="documents_data_origin_check",
        ),
        sa.CheckConstraint("char_length(body_text) > 0", name="documents_body_text_not_empty"),
    )
    
    op.create_index(
        "uq_documents_source_external",
        "documents",
        ["source_id", "external_id"],
        unique=True,
        postgresql_where=sa.text("external_id IS NOT NULL"),
    )
    op.create_index(
        "ix_documents_source_hash",
        "documents",
        ["source_id", "content_hash"],
    )
    op.create_index(
        "ix_documents_organization_id",
        "documents",
        ["organization_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_documents_organization_id", table_name="documents")
    op.drop_index("ix_documents_source_hash", table_name="documents")
    op.drop_index("uq_documents_source_external", table_name="documents")
    op.drop_table("documents")
