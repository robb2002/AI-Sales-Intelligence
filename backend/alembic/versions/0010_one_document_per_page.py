"""one current website document per organization and url; remove legacy copies

Revision ID: 0010
Revises: 0009
Create Date: 2026-09-24
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Website documents no longer tied to any approved page are copies from the earlier extractor.
    op.execute(
        """
        DELETE FROM documents d
        USING sources s
        WHERE d.source_id = s.source_id
          AND s.source_key LIKE 'website:%'
          AND d.organization_source_id IS NULL
        """
    )
    # A page with no readable text cannot own a document.
    op.execute(
        """
        DELETE FROM documents d
        USING organization_sources os
        WHERE d.organization_source_id = os.organization_source_id
          AND os.extraction_status = 'failed'
        """
    )
    # Keep only the latest version of each organization and URL.
    op.execute(
        """
        DELETE FROM documents d
        USING documents newer
        WHERE d.external_id IS NULL
          AND newer.external_id IS NULL
          AND d.organization_id = newer.organization_id
          AND d.source_url = newer.source_url
          AND (d.retrieved_at, d.document_id) < (newer.retrieved_at, newer.document_id)
        """
    )

    op.drop_index("uq_documents_source_hash", table_name="documents")
    op.create_index("ix_documents_source_hash", "documents", ["source_id", "content_hash"])
    op.create_index(
        "uq_documents_organization_url",
        "documents",
        ["organization_id", "source_url"],
        unique=True,
        postgresql_where=sa.text("external_id IS NULL AND organization_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_documents_organization_url", table_name="documents")
    op.drop_index("ix_documents_source_hash", table_name="documents")
    op.create_index(
        "uq_documents_source_hash", "documents", ["source_id", "content_hash"], unique=True
    )
