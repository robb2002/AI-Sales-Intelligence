"""Idempotent registry rows for SAM.gov, USAspending, and IPEDS.

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-23
"""
from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ROWS = (
    ("sam_gov", "SAM.gov", "https://sam.gov/opportunities", "official_api", "official_api"),
    (
        "usaspending",
        "USAspending.gov",
        "https://api.usaspending.gov/",
        "official_api",
        "official_api",
    ),
    (
        "ipeds",
        "NCES IPEDS",
        "https://nces.ed.gov/ipeds/",
        "official_data_file",
        None,
    ),
)


def upgrade() -> None:
    connection = op.get_bind()
    statement = text(
        """
        INSERT INTO sources (source_key, name, official_url, source_kind, reliability_label)
        VALUES (:source_key, :name, :official_url, :source_kind, :reliability_label)
        ON CONFLICT (source_key) DO UPDATE SET
            name = EXCLUDED.name,
            official_url = EXCLUDED.official_url,
            source_kind = EXCLUDED.source_kind,
            reliability_label = EXCLUDED.reliability_label,
            updated_at = now()
        """
    )
    for source_key, name, official_url, source_kind, reliability_label in _ROWS:
        connection.execute(
            statement,
            {
                "source_key": source_key,
                "name": name,
                "official_url": official_url,
                "source_kind": source_kind,
                "reliability_label": reliability_label,
            },
        )


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        text("DELETE FROM sources WHERE source_key = ANY(:keys)"),
        {"keys": [row[0] for row in _ROWS]},
    )
