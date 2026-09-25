"""sources hold DATA_SOURCES registry only; drop per-org website rows

Revision ID: 0012
Revises: 0011
Create Date: 2026-09-24
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("documents", "source_id", existing_type=sa.Uuid(), nullable=True)
    # Drop any website documents that never linked to an approved page (should be none).
    op.execute(
        """
        DELETE FROM documents
        WHERE organization_source_id IS NULL
          AND source_id IN (
              SELECT source_id FROM sources WHERE source_key LIKE 'website:%'
          )
        """
    )
    op.execute(
        """
        UPDATE documents
        SET source_id = NULL
        WHERE source_id IN (
            SELECT source_id FROM sources WHERE source_key LIKE 'website:%'
        )
        """
    )
    op.execute("DELETE FROM sources WHERE source_key LIKE 'website:%'")
    op.create_check_constraint(
        "documents_origin_present",
        "documents",
        "source_id IS NOT NULL OR organization_source_id IS NOT NULL",
    )


def downgrade() -> None:
    op.drop_constraint("documents_origin_present", "documents", type_="check")
    # Per-org website registry rows are not restored; website documents keep null source_id.
    op.alter_column("documents", "source_id", existing_type=sa.Uuid(), nullable=False)
