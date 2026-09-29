import asyncio
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

logger = logging.getLogger("app.database")

# The Supabase session pooler allows 15 clients for the whole project, shared by every
# developer's backend and script. Keep this small; scans release connections while they wait.
POOL_SIZE = 5


def create_engine(database_url: str) -> AsyncEngine:
    return create_async_engine(
        database_url, pool_size=POOL_SIZE, max_overflow=0, pool_pre_ping=True
    )


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def warm_pool(engine: AsyncEngine, count: int = POOL_SIZE) -> None:
    """Open `count` pooled connections up front. A new connection to the hosted database takes
    several seconds, so doing it at startup keeps that cost off the first page load."""
    results = await asyncio.gather(
        *(engine.connect() for _ in range(count)), return_exceptions=True
    )
    connections = [item for item in results if not isinstance(item, BaseException)]
    if len(connections) < count:
        logger.warning("Connection pool warm-up partly failed; connections will open on demand")
    try:
        for connection in connections:
            await connection.execute(text("select 1"))
    except Exception:
        logger.warning("Connection pool warm-up query failed")
    finally:
        for connection in connections:
            await connection.close()
