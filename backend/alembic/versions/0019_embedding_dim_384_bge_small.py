"""Resize document_chunks.embedding to 384 for local BAAI/bge-small-en-v1.5.

Revision ID: 0019
Revises: 0018
Create Date: 2026-09-25
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0019"
down_revision: str | None = "0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("UPDATE document_chunks SET embedding = NULL, embedding_model = NULL")
    op.execute(
        "ALTER TABLE document_chunks ALTER COLUMN embedding TYPE vector(384) "
        "USING NULL"
    )


def downgrade() -> None:
    op.execute("UPDATE document_chunks SET embedding = NULL, embedding_model = NULL")
    op.execute(
        "ALTER TABLE document_chunks ALTER COLUMN embedding TYPE vector(1024) "
        "USING NULL"
    )
