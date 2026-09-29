"""Live lookups for the Sales Persona, restricted to an allow-list.

Allowed hosts are the configured competitor domains (`PERSONA_ALLOWED_DOMAINS`) and the
official website of a tracked organization. Every request goes through the scan `Fetcher`
(robots.txt, honest User-Agent, per-host delay, same-domain redirects, no gated pages).
There is no open-web search and no path around a block. Excerpts are verbatim page text.
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from urllib.parse import urlparse

from app.core.config import Settings
from app.ingestion.fetcher import Fetcher, create_http_client
from app.ingestion.homepage_links import candidate_links
from app.ingestion.limiter import HostLimiter
from app.ingestion.normalizer import normalize_html
from app.ingestion.url_validation import extract_registrable_host, host_matches_official

# Shared so the per-host politeness gap also holds between consecutive chat requests.
_LIMITER = HostLimiter()

_EXCERPT_CHARS = 900
_STOP = frozenset(
    {"the", "and", "for", "with", "what", "whats", "latest", "news", "about", "from", "their"}
)


@dataclass(frozen=True)
class LiveHit:
    domain: str
    url: str
    title: str
    excerpt: str


@dataclass(frozen=True)
class LiveLookupResult:
    domain: str
    hits: list[LiveHit]
    failures: list[str]


def allowed_hosts(settings: Settings, organization_websites: list[str]) -> set[str]:
    hosts = set(settings.persona_domains)
    for website in organization_websites:
        host = extract_registrable_host(website or "")
        if host:
            hosts.add(host)
    return hosts


def is_allowed(host: str | None, allowed: set[str]) -> bool:
    return any(host_matches_official(host, entry) for entry in allowed)


def query_terms(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9]{4,}", text.lower())
    return [word for word in words if word not in _STOP][:8]


async def lookup_domains(
    settings: Settings,
    *,
    domains: list[str],
    allowed: set[str],
    query: str,
    max_pages_override: int | None = None,
) -> list[LiveLookupResult]:
    """Look up several allow-listed domains in parallel (different hosts do not block each other)."""
    if not settings.persona_live_lookup_enabled or not domains:
        return []
    safe = [d for d in dict.fromkeys(domains) if is_allowed(d, allowed)]
    if not safe:
        return []
    per_domain = max(1, settings.persona_max_live_pages_per_domain)
    if max_pages_override is not None:
        per_domain = max(1, min(per_domain, max_pages_override))
    elif len(safe) > 2:
        per_domain = min(per_domain, 2)
    terms = query_terms(query)
    async with create_http_client(settings) as client:
        fetcher = Fetcher(client, _LIMITER, settings)
        return list(
            await asyncio.gather(
                *(_lookup_one(fetcher, domain, terms, per_domain) for domain in safe)
            )
        )


async def _lookup_one(
    fetcher: Fetcher, domain: str, terms: list[str], max_pages: int
) -> LiveLookupResult:
    root = f"https://{domain}/"
    hits: list[LiveHit] = []
    failures: list[str] = []

    home = await fetcher.fetch(root, domain)
    if not home.ok or not home.html:
        return LiveLookupResult(domain, [], [f"{domain}: {home.reason or 'unreachable'}"])

    base = home.final_url or root
    page = normalize_html(home.html, base)
    hits.append(_hit(domain, base, page.title, page.body_text, terms))

    links = candidate_links(
        page.content_links or page.links, root_url=base, official_host=domain, max_links=12
    )
    for link in [item for item in links if item.rstrip("/") != base.rstrip("/")][: max_pages - 1]:
        fetched = await fetcher.fetch(link, domain)
        if not fetched.ok or not fetched.html:
            failures.append(f"{urlparse(link).path or '/'}: {fetched.reason or 'failed'}")
            continue
        sub = normalize_html(fetched.html, fetched.final_url or link)
        hits.append(_hit(domain, fetched.final_url or link, sub.title, sub.body_text, terms))

    return LiveLookupResult(domain, [h for h in hits if h.excerpt], failures)


def _hit(domain: str, url: str, title: str | None, body: str, terms: list[str]) -> LiveHit:
    return LiveHit(
        domain=domain,
        url=url,
        title=(title or domain).strip()[:160],
        excerpt=_excerpt(body, terms),
    )


def _excerpt(body: str, terms: list[str]) -> str:
    """Verbatim paragraphs, preferring ones that mention the question's terms."""
    paragraphs = [p.strip() for p in body.split("\n\n") if len(p.strip()) >= 40]
    if not paragraphs:
        return ""
    scored = sorted(
        enumerate(paragraphs),
        key=lambda item: (-sum(term in item[1].lower() for term in terms), item[0]),
    )
    chosen: list[str] = []
    total = 0
    for _index, paragraph in scored:
        if total + len(paragraph) > _EXCERPT_CHARS and chosen:
            break
        chosen.append(paragraph[:_EXCERPT_CHARS])
        total += len(paragraph)
    return "\n".join(chosen)
