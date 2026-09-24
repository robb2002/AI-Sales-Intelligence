"""Idempotent seed of the ten MVP TARGET organizations.

Official root site URLs only. No news, technology, or procurement deep links.
ONLINE_UNIVERSITY from the seed brief maps to API enum `university`.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.organizations import Organization

# Stable natural key: website_url (unique). Re-runs update name/type/status only.
TARGET_ORGANIZATIONS: tuple[dict[str, str], ...] = (
    {
        "name": "Arizona State University",
        "organization_type": "university",
        "market_role": "target",
        "tracking_status": "active",
        "state_code": "AZ",
        "website_url": "https://asu.edu",
    },
    {
        "name": "University of Central Florida",
        "organization_type": "university",
        "market_role": "target",
        "tracking_status": "active",
        "state_code": "FL",
        "website_url": "https://ucf.edu",
    },
    {
        "name": "Purdue University",
        "organization_type": "university",
        "market_role": "target",
        "tracking_status": "inactive",
        "state_code": "IN",
        "website_url": "https://purdue.edu",
    },
    {
        "name": "University of Maryland Global Campus",
        "organization_type": "university",
        "market_role": "target",
        "tracking_status": "inactive",
        "state_code": "MD",
        "website_url": "https://umgc.edu",
    },
    {
        "name": "Western Governors University",
        "organization_type": "university",
        "market_role": "target",
        "tracking_status": "inactive",
        "state_code": "UT",
        "website_url": "https://wgu.edu",
    },
    {
        "name": "Pennsylvania State University",
        "organization_type": "university",
        "market_role": "target",
        "tracking_status": "inactive",
        "state_code": "PA",
        "website_url": "https://psu.edu",
    },
    {
        "name": "University of Florida",
        "organization_type": "university",
        "market_role": "target",
        "tracking_status": "inactive",
        "state_code": "FL",
        "website_url": "https://ufl.edu",
    },
    {
        "name": "Georgia State University",
        "organization_type": "university",
        "market_role": "target",
        "tracking_status": "inactive",
        "state_code": "GA",
        "website_url": "https://gsu.edu",
    },
    {
        "name": "University of Illinois Urbana-Champaign",
        "organization_type": "university",
        "market_role": "target",
        "tracking_status": "inactive",
        "state_code": "IL",
        "website_url": "https://illinois.edu",
    },
    {
        "name": "University of Michigan",
        "organization_type": "university",
        "market_role": "target",
        "tracking_status": "inactive",
        "state_code": "MI",
        "website_url": "https://umich.edu",
    },
)


async def seed_target_organizations(session: AsyncSession) -> dict[str, int]:
    """Upsert the ten TARGET organizations. Safe to run more than once."""
    for row in TARGET_ORGANIZATIONS:
        statement = (
            insert(Organization)
            .values(**row)
            .on_conflict_do_update(
                index_elements=[Organization.website_url],
                set_={
                    "name": row["name"],
                    "organization_type": row["organization_type"],
                    "market_role": row["market_role"],
                    "tracking_status": row["tracking_status"],
                    "state_code": row["state_code"],
                },
            )
        )
        await session.execute(statement)
    await session.commit()

    total_count = await session.scalar(
        select(func.count()).select_from(Organization).where(Organization.market_role == "target")
    )
    active_count = await session.scalar(
        select(func.count())
        .select_from(Organization)
        .where(
            Organization.market_role == "target",
            Organization.tracking_status == "active",
        )
    )
    inactive_count = await session.scalar(
        select(func.count())
        .select_from(Organization)
        .where(
            Organization.market_role == "target",
            Organization.tracking_status == "inactive",
        )
    )
    return {
        "target_total": int(total_count or 0),
        "active": int(active_count or 0),
        "inactive": int(inactive_count or 0),
    }


async def _run() -> None:
    from app.core.config import get_settings
    from app.core.database import create_engine, create_session_factory

    engine = create_engine(get_settings().database_url)
    session_factory = create_session_factory(engine)
    async with session_factory() as session:
        counts = await seed_target_organizations(session)
    await engine.dispose()
    print(
        f"Seeded TARGET organizations: total={counts['target_total']} "
        f"active={counts['active']} inactive={counts['inactive']}"
    )


if __name__ == "__main__":
    import asyncio

    asyncio.run(_run())
