from __future__ import annotations

import asyncio
import ipaddress
import logging
import socket
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx

from app.core.config import Settings
from app.ingestion.limiter import HostLimiter
from app.ingestion.url_validation import host_matches_official, looks_gated

logger = logging.getLogger("app.ingestion.fetcher")

_MAX_REDIRECTS = 5
_MAX_HTML_CHARS = 2_000_000
_RETRYABLE_STATUS = frozenset({500, 502, 503, 504})


@dataclass(frozen=True)
class FetchResult:
    ok: bool
    requested_url: str
    final_url: str | None
    http_status: int | None
    html: str | None
    reason: str | None
    retrieved_at: datetime | None


def create_http_client(settings: Settings) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        headers={
            "User-Agent": settings.http_user_agent,
            "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.5",
        },
        timeout=httpx.Timeout(settings.http_timeout_seconds, connect=10.0),
        follow_redirects=False,
    )


class Fetcher:
    """The only path for website requests: robots, honest user agent, per-host delay,
    same-domain redirects, bounded retry. There is no path around a block or a disallow."""

    def __init__(self, client: httpx.AsyncClient, limiter: HostLimiter, settings: Settings) -> None:
        self._client = client
        self._limiter = limiter
        self._user_agent = settings.http_user_agent
        self._in_flight = asyncio.Semaphore(max(1, settings.scan_max_concurrent_sources))
        self._robots: dict[str, RobotFileParser | None] = {}
        self._robots_locks: dict[str, asyncio.Lock] = {}
        self._unsafe_hosts: dict[str, str | None] = {}
        self._blocked_hosts: set[str] = set()

    async def fetch(self, url: str, official_host: str) -> FetchResult:
        current = url
        for _ in range(_MAX_REDIRECTS + 1):
            parsed = urlparse(current)
            if parsed.scheme not in ("http", "https") or not parsed.hostname:
                return _fail(url, "invalid_url_syntax")
            host = parsed.hostname.lower()
            if not host_matches_official(host, official_host):
                return _fail(url, "domain_mismatch" if current == url else "redirect_domain_mismatch")
            if host in self._blocked_hosts:
                return _fail(url, "host_rate_limited")

            unsafe = await self._unsafe_reason(host)
            if unsafe:
                return _fail(url, unsafe)

            robots_reason = await self._robots_reason(current)
            if robots_reason:
                return _fail(url, robots_reason)

            response, error = await self._get_with_retry(host, current)
            if response is None:
                return _fail(url, error or "http_failure")

            if response.is_redirect:
                location = response.headers.get("location")
                if not location:
                    return _fail(url, "redirect_failure", response.status_code)
                current = urljoin(current, location)
                continue

            return self._finish(url, current, response)

        return _fail(url, "redirect_failure")

    def _finish(self, url: str, final_url: str, response: httpx.Response) -> FetchResult:
        status = response.status_code
        if status == 429:
            self._blocked_hosts.add(urlparse(final_url).hostname or "")
        if status >= 400:
            return FetchResult(False, url, final_url, status, None, f"http_{status}", None)

        content_type = (response.headers.get("content-type") or "").lower()
        if content_type and "html" not in content_type:
            return FetchResult(False, url, final_url, status, None, "not_html", None)

        html = response.text[:_MAX_HTML_CHARS] if response.text else ""
        if not html.strip():
            return FetchResult(False, url, final_url, status, None, "empty_page", None)
        if looks_gated(html):
            return FetchResult(False, url, final_url, status, None, "access_restricted", None)

        return FetchResult(True, url, final_url, status, html, None, datetime.now(timezone.utc))

    async def _get_with_retry(
        self, host: str, url: str
    ) -> tuple[httpx.Response | None, str | None]:
        error: str | None = None
        for attempt in range(2):
            try:
                async with self._limiter.slot(host), self._in_flight:
                    response = await self._client.get(url)
            except httpx.TimeoutException:
                error = "timeout"
                continue
            except httpx.HTTPError as exc:
                logger.info("Fetch failed", extra={"fields": {"host": host, "error": type(exc).__name__}})
                error = "http_failure"
                continue
            if response.status_code in _RETRYABLE_STATUS and attempt == 0:
                error = f"http_{response.status_code}"
                continue
            return response, None
        return None, error

    async def _robots_reason(self, url: str) -> str | None:
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        lock = self._robots_locks.setdefault(origin, asyncio.Lock())
        async with lock:
            if origin not in self._robots:
                self._robots[origin] = await self._load_robots(origin, parsed.hostname or "")
        parser = self._robots[origin]
        if parser is None:
            return "robots_unavailable"
        if not parser.can_fetch(self._user_agent, url):
            return "robots_disallow"
        return None

    async def _load_robots(self, origin: str, host: str) -> RobotFileParser | None:
        parser = RobotFileParser()
        try:
            async with self._limiter.slot(host), self._in_flight:
                response = await self._client.get(f"{origin}/robots.txt", follow_redirects=True)
        except httpx.HTTPError:
            return None
        # RFC 9309: 4xx means no restrictions; 5xx means assume full disallow.
        if response.status_code >= 500:
            return None
        if response.status_code in (401, 403):
            parser.disallow_all = True
        elif response.status_code >= 400:
            parser.allow_all = True
        else:
            parser.parse(response.text.splitlines())
            self._limiter.set_crawl_delay(host, parser.crawl_delay(self._user_agent))
        return parser

    async def _unsafe_reason(self, host: str) -> str | None:
        if host in self._unsafe_hosts:
            return self._unsafe_hosts[host]
        reason: str | None = None
        try:
            infos = await asyncio.to_thread(socket.getaddrinfo, host, None)
        except socket.gaierror:
            reason = "dns_failure"
        else:
            for info in infos:
                ip = ipaddress.ip_address(info[4][0])
                if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                    reason = "unsafe_address"
                    break
        self._unsafe_hosts[host] = reason
        return reason


def _fail(url: str, reason: str, status: int | None = None) -> FetchResult:
    return FetchResult(False, url, None, status, None, reason, None)
