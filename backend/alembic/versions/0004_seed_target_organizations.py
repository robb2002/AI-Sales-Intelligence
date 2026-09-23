"""seed target organizations

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-23
"""
from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Idempotent upsert on website_url. ONLINE_UNIVERSITY maps to university.
_SEED_ROWS = (
    ("Arizona State University", "university", "target", "active", "AZ", "https://asu.edu"),
    ("University of Central Florida", "university", "target", "active", "FL", "https://ucf.edu"),
    ("Purdue University", "university", "target", "inactive", "IN", "https://purdue.edu"),
    ("University of Maryland Global Campus", "university", "target", "inactive", "MD", "https://umgc.edu"),
    ("Western Governors University", "university", "target", "inactive", "UT", "https://wgu.edu"),
    ("Pennsylvania State University", "university", "target", "inactive", "PA", "https://psu.edu"),
    ("University of Florida", "university", "target", "inactive", "FL", "https://ufl.edu"),
    ("Georgia State University", "university", "target", "inactive", "GA", "https://gsu.edu"),
    ("University of Illinois Urbana-Champaign", "university", "target", "inactive", "IL", "https://illinois.edu"),
    ("University of Michigan", "university", "target", "inactive", "MI", "https://umich.edu"),
)


def upgrade() -> None:
    connection = op.get_bind()
    statement = text(
        """
        INSERT INTO organizations (
            name, organization_type, market_role, tracking_status, state_code, website_url
        ) VALUES (
            :name, :organization_type, :market_role, :tracking_status, :state_code, :website_url
        )
        ON CONFLICT (website_url) DO UPDATE SET
            name = EXCLUDED.name,
            organization_type = EXCLUDED.organization_type,
            market_role = EXCLUDED.market_role,
            tracking_status = EXCLUDED.tracking_status,
            state_code = EXCLUDED.state_code,
            updated_at = now()
        """
    )
    for name, organization_type, market_role, tracking_status, state_code, website_url in _SEED_ROWS:
        connection.execute(
            statement,
            {
                "name": name,
                "organization_type": organization_type,
                "market_role": market_role,
                "tracking_status": tracking_status,
                "state_code": state_code,
                "website_url": website_url,
            },
        )


def downgrade() -> None:
    connection = op.get_bind()
    urls = [row[5] for row in _SEED_ROWS]
    connection.execute(
        text("DELETE FROM organizations WHERE website_url = ANY(:urls)"),
        {"urls": urls},
    )
