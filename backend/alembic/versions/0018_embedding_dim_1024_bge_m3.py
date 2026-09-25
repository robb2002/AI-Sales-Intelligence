"""Resize document_chunks.embedding to 1024 for local BAAI/bge-m3.

Revision ID: 0018
Revises: 0017
Create Date: 2026-09-25
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0018"
down_revision: str | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("UPDATE document_chunks SET embedding = NULL, embedding_model = NULL")
    op.execute(
        "ALTER TABLE document_chunks ALTER COLUMN embedding TYPE vector(1024) "
        "USING NULL"
    )


def downgrade() -> None:
    op.execute("UPDATE document_chunks SET embedding = NULL, embedding_model = NULL")
    op.execute(
        "ALTER TABLE document_chunks ALTER COLUMN embedding TYPE vector(768) "
        "USING NULL"
    )
