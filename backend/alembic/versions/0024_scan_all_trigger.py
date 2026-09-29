"""create scan_all_trigger (singleton row for the manager-set Scan All schedule)

Revision ID: 0024
Revises: 0023
Create Date: 2026-09-29

Purely additive: one new table, seeded with its single row. No existing table changed.
Mirrors 0023's per-organization schedule, but for Scan All (all active target organizations).
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0024"
down_revision: str | None = "0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "scan_all_trigger",
        sa.Column("id", sa.SmallInteger(), primary_key=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("id = 1", name="scan_all_trigger_singleton_check"),
    )
    op.execute("INSERT INTO scan_all_trigger (id, scheduled_at) VALUES (1, NULL)")


def downgrade() -> None:
    op.drop_table("scan_all_trigger")
