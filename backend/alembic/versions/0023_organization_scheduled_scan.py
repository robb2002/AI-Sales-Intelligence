"""add organizations.scheduled_scan_at

Revision ID: 0023
Revises: 0022
Create Date: 2026-09-29

Purely additive: one new nullable column. No existing column, constraint, or table changes.
A manager sets a future UTC date/time on an organization (Edit organization, "Schedule" tab);
an always-on background checker (app/scheduled_scan_trigger.py) starts that organization's scan
when the time is reached, then clears the column. Independent of the daily Scan All scheduler
and its SCHEDULER_ENABLED toggle.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0023"
down_revision: str | None = "0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "organizations",
        sa.Column("scheduled_scan_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("organizations", "scheduled_scan_at")
