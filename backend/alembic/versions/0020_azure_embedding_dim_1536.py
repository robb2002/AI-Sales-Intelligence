"""Clear document_chunks and restore embedding column to vector(1536) for Azure.

Revision ID: 0020
Revises: 0019
Create Date: 2026-09-25
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0020"
down_revision: str | None = "0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Drop stale local/Groq vectors only. Parent documents and signals stay.
    op.execute("DELETE FROM document_chunks")
    op.execute(
        "ALTER TABLE document_chunks ALTER COLUMN embedding TYPE vector(1536) "
        "USING NULL"
    )


def downgrade() -> None:
    op.execute("DELETE FROM document_chunks")
    op.execute(
        "ALTER TABLE document_chunks ALTER COLUMN embedding TYPE vector(384) "
        "USING NULL"
    )
