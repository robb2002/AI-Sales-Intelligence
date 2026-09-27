"""add edtech_company organization type and seed competitor organizations

Revision ID: 0021
Revises: 0020
Create Date: 2026-09-26
"""
from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

revision: str = "0021"
down_revision: str | None = "0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_OLD_TYPES = "'university', 'college', 'k12_district', 'public_sector_education'"
_NEW_TYPES = _OLD_TYPES + ", 'edtech_company'"

# COMPETITOR organizations (DATA_SOURCES.md target data model). Same pipeline as a TARGET,
# but never an opportunity. Idempotent on website_url.
_COMPETITORS = (
    ("Honorlock", "https://honorlock.com"),
    ("Proctorio", "https://proctorio.com"),
    ("Meazure Learning", "https://meazurelearning.com"),
    ("Caveon", "https://caveon.com"),
    ("Questionmark", "https://questionmark.com"),
)


def upgrade() -> None:
    op.drop_constraint("organizations_organization_type_check", "organizations", type_="check")
    op.create_check_constraint(
        "organizations_organization_type_check",
        "organizations",
        f"organization_type IN ({_NEW_TYPES})",
    )
    connection = op.get_bind()
    statement = text(
        """
        INSERT INTO organizations (
            name, organization_type, market_role, tracking_status, state_code, website_url
        ) VALUES (:name, 'edtech_company', 'competitor', 'active', NULL, :website_url)
        ON CONFLICT (website_url) DO UPDATE SET
            name = EXCLUDED.name,
            organization_type = EXCLUDED.organization_type,
            market_role = EXCLUDED.market_role,
            updated_at = now()
        """
    )
    for name, website_url in _COMPETITORS:
        connection.execute(statement, {"name": name, "website_url": website_url})


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(text("DELETE FROM organizations WHERE market_role = 'competitor'"))
    op.drop_constraint("organizations_organization_type_check", "organizations", type_="check")
    op.create_check_constraint(
        "organizations_organization_type_check",
        "organizations",
        f"organization_type IN ({_OLD_TYPES})",
    )
