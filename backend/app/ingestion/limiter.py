from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

# DATA_SOURCES.md §5.4: at least five seconds between requests to the same host,
# or the robots.txt crawl-delay when that is longer.
MIN_HOST_DELAY_SECONDS = 5.0


class HostLimiter:
    """Serializes requests per host with a politeness gap. Different hosts run in parallel."""

    def __init__(self) -> None:
        self._locks: dict[str, asyncio.Lock] = {}
        self._next_allowed: dict[str, float] = {}
        self._delays: dict[str, float] = {}

    def set_crawl_delay(self, host: str, seconds: float | None) -> None:
        if seconds and seconds > MIN_HOST_DELAY_SECONDS:
            self._delays[host] = float(seconds)

    @asynccontextmanager
    async def slot(self, host: str) -> AsyncIterator[None]:
        loop = asyncio.get_running_loop()
        lock = self._locks.setdefault(host, asyncio.Lock())
        async with lock:
            wait = self._next_allowed.get(host, 0.0) - loop.time()
            if wait > 0:
                await asyncio.sleep(wait)
            try:
                yield
            finally:
                delay = self._delays.get(host, MIN_HOST_DELAY_SECONDS)
                self._next_allowed[host] = loop.time() + delay
