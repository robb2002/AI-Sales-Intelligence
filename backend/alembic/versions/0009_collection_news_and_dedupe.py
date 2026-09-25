"""news page category, document to page link, one document per content hash

Revision ID: 0009
Revises: 0008
Create Date: 2026-09-24
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CATEGORIES = (
    "'procurement', 'technology', 'digital_learning', 'assessment', "
    "'funding', 'leadership', 'strategic_initiative', 'partnership'"
)


def upgrade() -> None:
    op.drop_constraint(
        "organization_sources_page_category_check", "organization_sources", type_="check"
    )
    op.create_check_constraint(
        "organization_sources_page_category_check",
        "organization_sources",
        f"page_category IN ({_CATEGORIES}, 'news')",
    )

    op.add_column("documents", sa.Column("organization_source_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "documents_organization_source_id_fkey",
        "documents",
        "organization_sources",
        ["organization_source_id"],
        ["organization_source_id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_documents_organization_source_id", "documents", ["organization_source_id"]
    )

    op.execute(
        """
        DELETE FROM documents d
        USING documents keep
        WHERE d.source_id = keep.source_id
          AND d.content_hash = keep.content_hash
          AND (d.created_at, d.document_id) > (keep.created_at, keep.document_id)
        """
    )
    op.drop_index("ix_documents_source_hash", table_name="documents")
    op.create_index(
        "uq_documents_source_hash", "documents", ["source_id", "content_hash"], unique=True
    )
    op.execute(
        """
        UPDATE documents d
        SET organization_source_id = os.organization_source_id
        FROM organization_sources os
        WHERE d.organization_source_id IS NULL
          AND d.organization_id = os.organization_id
          AND rtrim(replace(d.source_url, '://www.', '://'), '/') = rtrim(os.url, '/')
        """
    )
    op.execute("UPDATE organization_sources SET extraction_status = 'pending'")

    op.add_column(
        "scan_runs",
        sa.Column("documents_collected", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_check_constraint(
        "scan_runs_documents_collected_check", "scan_runs", "documents_collected >= 0"
    )


def downgrade() -> None:
    op.drop_constraint("scan_runs_documents_collected_check", "scan_runs", type_="check")
    op.drop_column("scan_runs", "documents_collected")

    op.drop_index("uq_documents_source_hash", table_name="documents")
    op.create_index("ix_documents_source_hash", "documents", ["source_id", "content_hash"])
    op.drop_index("ix_documents_organization_source_id", table_name="documents")
    op.drop_constraint("documents_organization_source_id_fkey", "documents", type_="foreignkey")
    op.drop_column("documents", "organization_source_id")

    op.execute("UPDATE organization_sources SET page_category = 'strategic_initiative' WHERE page_category = 'news'")
    op.drop_constraint(
        "organization_sources_page_category_check", "organization_sources", type_="check"
    )
    op.create_check_constraint(
        "organization_sources_page_category_check",
        "organization_sources",
        f"page_category IN ({_CATEGORIES})",
    )
