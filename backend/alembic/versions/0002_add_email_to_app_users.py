"""add email to app_users

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-23
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "app_users",
        sa.Column("email", sa.Text(), nullable=False, server_default=""),
    )
    op.alter_column("app_users", "email", server_default=None)


def downgrade() -> None:
    op.drop_column("app_users", "email")
