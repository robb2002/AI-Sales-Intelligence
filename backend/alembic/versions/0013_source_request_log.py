"""Durable log of outbound registry API requests (SAM.gov quota)

Revision ID: 0013
Revises: 0012
Create Date: 2026-09-24
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "source_request_log",
        sa.Column(
            "request_id",
            sa.Uuid(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("source_key", sa.Text(), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("outcome", sa.Text(), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "outcome IN ('ok', 'error', 'quota_blocked', 'rejected')",
            name="source_request_log_outcome_check",
        ),
    )
    op.create_index(
        "ix_source_request_log_source_requested",
        "source_request_log",
        ["source_key", "requested_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_source_request_log_source_requested", table_name="source_request_log")
    op.drop_table("source_request_log")
