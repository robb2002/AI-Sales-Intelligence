"""record which user started a scan

Revision ID: 0011
Revises: 0010
Create Date: 2026-09-24
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("scan_runs", sa.Column("requested_by_user_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "scan_runs_requested_by_user_id_fkey",
        "scan_runs",
        "app_users",
        ["requested_by_user_id"],
        ["user_id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("scan_runs_requested_by_user_id_fkey", "scan_runs", type_="foreignkey")
    op.drop_column("scan_runs", "requested_by_user_id")
