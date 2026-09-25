"""Resize document_chunks.embedding to 768 for Groq nomic-embed-text.

Revision ID: 0017
Revises: 0016
Create Date: 2026-09-25
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0017"
down_revision: str | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Old Azure-width vectors cannot cast to 768; clear and rebuild on next scan.
    op.execute("UPDATE document_chunks SET embedding = NULL, embedding_model = NULL")
    op.execute(
        "ALTER TABLE document_chunks ALTER COLUMN embedding TYPE vector(768) "
        "USING NULL"
    )


def downgrade() -> None:
    op.execute("UPDATE document_chunks SET embedding = NULL, embedding_model = NULL")
    op.execute(
        "ALTER TABLE document_chunks ALTER COLUMN embedding TYPE vector(1536) "
        "USING NULL"
    )
