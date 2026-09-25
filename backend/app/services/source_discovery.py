from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit, urlunsplit

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.adapters.base import LLMProviderAdapter, SourceCandidate
from app.core.config import Settings
from app.ingestion.fetcher import Fetcher, FetchResult
from app.ingestion.homepage_links import (
    candidate_links,
    guess_page_category,
    is_news_hub,
    is_reusable_source_url,
    title_from_path,
)
from app.ingestion.normalizer import normalize_html
from app.ingestion.url_validation import extract_registrable_host
from app.repositories import organization_sources as organization_sources_repo
from app.repositories.organization_sources import OrganizationSource
from app.repositories.organizations import Organization
from app.repositories.scans import ScanRun

logger = logging.getLogger("app.services.source_discovery")

_TRANSIENT_REASONS = frozenset(
    {"timeout", "http_failure", "robots_unavailable", "host_rate_limited", "http_429", "dns_failure"}
)


@dataclass(frozen=True)
class ApprovedPage:
    organization_source_id: uuid.UUID
    url: str
    page_category: str
    title: str | None
    fetched: FetchResult | None


async def run_organization_discovery(
    session: AsyncSession,
    *,
    settings: Settings,
    llm: LLMProviderAdapter,
    fetcher: Fetcher,
    scan: ScanRun,
    org: Organization,
) -> list[ApprovedPage] | None:
    """Discover and validate official pages for one organization. Every page is fetched at
    most once; the fetched HTML travels with the result so collection does not fetch again."""
    organization_id = org.organization_id
    scan.status = "running"
    scan.stage = "discovering"
    scan.started_at = datetime.now(timezone.utc)
    scan.error_detail = None
    await session.commit()

    official_host = extract_registrable_host(org.website_url or "")
    if not official_host:
        await _fail(session, scan, "Organization has no official website_url")
        return None
    root_url = _normalize_url(org.website_url if "://" in (org.website_url or "") else f"https://{official_host}")

    await _collapse_url_aliases(session, organization_id=organization_id)
    await session.commit()

    existing_approved = list(
        (
            await session.execute(
                select(OrganizationSource).where(
                    OrganizationSource.organization_id == organization_id,
                    OrganizationSource.status == "approved",
                )
            )
        ).scalars().all()
    )
    existing_by_url = {_normalize_url(row.url): row for row in existing_approved}
    since = datetime.now(timezone.utc) - timedelta(hours=max(0, settings.scan_refresh_hours))
    fresh_ids = await organization_sources_repo.fresh_source_ids(session, organization_id, since)
    page_cache: dict[str, FetchResult] = {}

    root_row = existing_by_url.get(root_url)
    if root_row is not None and root_row.organization_source_id in fresh_ids:
        # Inside the refresh window: no homepage fetch and no model call.
        candidates = [
            SourceCandidate(row.url, row.source_title, row.page_category, "previously approved")
            for row in existing_approved
        ]
    else:
        candidates = await _discover_candidates(
            settings=settings,
            llm=llm,
            fetcher=fetcher,
            org=org,
            official_host=official_host,
            root_url=root_row.url if root_row is not None else root_url,
            existing_urls=[row.url for row in existing_approved],
            page_cache=page_cache,
        )
    candidates = _prioritize(candidates, root_url, settings.scan_max_pages_per_organization)

    scan.candidates_found = len(candidates)
    scan.stage = "validating_sources"
    scan.sources = []
    await session.commit()

    def is_fresh(candidate: SourceCandidate) -> bool:
        row = existing_by_url.get(_normalize_url(candidate.url))
        return row is not None and row.organization_source_id in fresh_ids

    to_fetch = [candidate for candidate in candidates if not is_fresh(candidate)]
    fetched = await asyncio.gather(
        *[_fetch_cached(fetcher, c.url, official_host, page_cache) for c in to_fetch]
    )
    results = dict(zip((c.url for c in to_fetch), fetched))

    approved: list[ApprovedPage] = []
    rejected = 0
    source_rows: list[dict] = []
    seen_final: set[str] = set()

    for candidate in candidates:
        prior = existing_by_url.get(_normalize_url(candidate.url))
        if candidate.url not in results and prior is not None:
            approved.append(
                ApprovedPage(prior.organization_source_id, prior.url, prior.page_category, prior.source_title, None)
            )
            seen_final.add(_normalize_url(prior.url))
            source_rows.append(
                {"source_name": prior.source_title or prior.url, "status": "skipped", "detail": "collected within refresh window"}
            )
            continue

        result = results[candidate.url]
        if result.ok and result.final_url:
            final_url = _strip_fragment(result.final_url)
            if _normalize_url(final_url) in seen_final:
                continue
            seen_final.add(_normalize_url(final_url))
            source_id = await _upsert_source(
                session,
                organization_id=organization_id,
                url=final_url,
                title=candidate.title,
                page_category=candidate.page_category,
                status="approved",
                rejection_reason=None,
            )
            approved.append(ApprovedPage(source_id, final_url, candidate.page_category, candidate.title, result))
            source_rows.append(
                {"source_name": candidate.title or final_url, "status": "succeeded", "detail": candidate.page_category}
            )
            continue

        reason = result.reason or "validation_failed"
        if prior is None and result.final_url:
            prior = existing_by_url.get(_normalize_url(result.final_url))
        if prior is not None and _is_transient(reason):
            # A network hiccup does not demote a page that was approved before.
            source_rows.append(
                {"source_name": prior.source_title or prior.url, "status": "failed", "detail": f"{reason}; kept previous approval"}
            )
            rejected += 1
            continue

        rejected += 1
        if result.final_url and _host_ok(result.final_url, official_host):
            await _upsert_source(
                session,
                organization_id=organization_id,
                url=_strip_fragment(result.final_url),
                title=candidate.title,
                page_category=candidate.page_category,
                status="rejected",
                rejection_reason=reason,
            )
        source_rows.append({"source_name": candidate.title or candidate.url, "status": "failed", "detail": reason})

    scan.stage = "saving_sources"
    scan.sources = source_rows
    scan.sources_approved = len(approved)
    scan.sources_rejected = rejected
    await session.commit()

    if not approved:
        await _fail(session, scan, "No candidate passed validation")
        return None
    return approved


async def _discover_candidates(
    *,
    settings: Settings,
    llm: LLMProviderAdapter,
    fetcher: Fetcher,
    org: Organization,
    official_host: str,
    root_url: str,
    existing_urls: list[str],
    page_cache: dict[str, FetchResult],
) -> list[SourceCandidate]:
    root = await _fetch_cached(fetcher, root_url, official_host, page_cache)
    links: list[str] = []
    if root.ok and root.html and root.final_url:
        page = await asyncio.to_thread(normalize_html, root.html, root.final_url)
        links = page.links

    discovered = candidate_links(links, root_url=root_url, official_host=official_host)
    discovered = [url for url in _unique_urls([*discovered, *existing_urls]) if is_reusable_source_url(url)]

    try:
        selected = await llm.propose_organization_urls(
            organization_name=org.name,
            official_domain=official_host,
            candidate_urls=discovered,
        )
    except Exception:
        logger.exception("LLM discovery failed; falling back to rule-based selection")
        selected = []

    if not selected:
        selected = [
            SourceCandidate(
                url=url,
                title=title_from_path(url) or f"{org.name} official page",
                page_category=guess_page_category(url),
                reason="Rule-based selection from official homepage links",
            )
            for url in discovered[:8]
        ]

    candidates = [
        SourceCandidate(root_url, f"{org.name} official site", "strategic_initiative", "Official domain root"),
        *[item for item in selected if is_reusable_source_url(item.url)],
    ]
    if not any(is_news_hub(item.url) for item in candidates):
        hub = next((url for url in discovered if is_news_hub(url)), None)
        if hub:
            candidates.append(SourceCandidate(hub, f"{org.name} news", "news", "Official news hub"))
    return candidates


def _prioritize(candidates: list[SourceCandidate], root_url: str, limit: int) -> list[SourceCandidate]:
    """Root first, then news hubs, then the rest; one entry per URL; capped per organization."""
    normalized: list[SourceCandidate] = []
    for item in _dedupe_candidates(candidates):
        category = "news" if is_news_hub(item.url) else item.page_category
        normalized.append(SourceCandidate(item.url, item.title, category, item.reason))
    ordered = sorted(
        normalized,
        key=lambda item: (
            _normalize_url(item.url) != root_url,
            item.page_category != "news",
        ),
    )
    return ordered[: max(1, limit)]


async def _fetch_cached(
    fetcher: Fetcher, url: str, official_host: str, cache: dict[str, FetchResult]
) -> FetchResult:
    key = _normalize_url(url)
    if key in cache:
        return cache[key]
    result = await fetcher.fetch(url, official_host)
    cache[key] = result
    if result.final_url:
        cache.setdefault(_normalize_url(result.final_url), result)
    return result


async def _fail(session: AsyncSession, scan: ScanRun, detail: str) -> None:
    scan.status = "failed"
    scan.stage = None
    scan.error_detail = detail
    scan.finished_at = datetime.now(timezone.utc)
    await session.commit()


async def _upsert_source(
    session: AsyncSession,
    *,
    organization_id,
    url: str,
    title: str | None,
    page_category: str,
    status: str,
    rejection_reason: str | None,
) -> uuid.UUID:
    """Store the exact URL that was fetched; www and trailing-slash variants of it are
    the same page and are removed so one row remains."""
    now = datetime.now(timezone.utc)
    normalized = _normalize_url(url)
    aliases = [alias for alias in [normalized, *_alias_urls(normalized)] if alias != url]
    await session.execute(
        delete(OrganizationSource).where(
            OrganizationSource.organization_id == organization_id,
            OrganizationSource.url.in_(aliases),
        )
    )
    statement = (
        insert(OrganizationSource)
        .values(
            organization_id=organization_id,
            url=url,
            source_title=title,
            page_category=page_category,
            status=status,
            extraction_status="pending",
            is_official=True,
            rejection_reason=rejection_reason,
            last_validated_at=now,
        )
        .on_conflict_do_update(
            constraint="organization_sources_organization_id_url_key",
            set_={
                "source_title": title,
                "page_category": page_category,
                "status": status,
                "extraction_status": "pending",
                "is_official": True,
                "rejection_reason": rejection_reason,
                "last_validated_at": now,
                "updated_at": now,
            },
        )
        .returning(OrganizationSource.organization_source_id)
    )
    return (await session.execute(statement)).scalar_one()


async def _collapse_url_aliases(session: AsyncSession, *, organization_id) -> None:
    rows = (
        await session.execute(
            select(OrganizationSource).where(
                OrganizationSource.organization_id == organization_id
            )
        )
    ).scalars().all()
    best: dict[str, OrganizationSource] = {}
    remove_ids = []
    for row in rows:
        key = _normalize_url(row.url)
        current = best.get(key)
        if current is None:
            best[key] = row
            continue
        keep_new = False
        if row.status == "approved" and current.status != "approved":
            keep_new = True
        elif row.status == current.status and row.last_validated_at >= current.last_validated_at:
            keep_new = True
        if keep_new:
            remove_ids.append(current.organization_source_id)
            best[key] = row
        else:
            remove_ids.append(row.organization_source_id)

    if remove_ids:
        await session.execute(
            delete(OrganizationSource).where(
                OrganizationSource.organization_source_id.in_(remove_ids)
            )
        )


def _strip_fragment(url: str) -> str:
    parts = urlsplit(url.strip())
    return urlunsplit((parts.scheme, parts.netloc, parts.path or "/", parts.query, ""))


def _alias_urls(normalized: str) -> list[str]:
    parts = urlsplit(normalized)
    host = parts.netloc
    path = parts.path
    variants = {path, path.rstrip("/") or "/", path if path.endswith("/") else path + "/"}
    aliases = {
        urlunsplit((parts.scheme, h, p, "", ""))
        for h in (host, f"www.{host}")
        for p in variants
    }
    aliases.discard(normalized)
    return sorted(aliases)


def _normalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    host = parts.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    path = parts.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    return urlunsplit((parts.scheme.lower(), host, path, "", ""))


def _dedupe_candidates(candidates: list[SourceCandidate]) -> list[SourceCandidate]:
    seen: set[str] = set()
    out: list[SourceCandidate] = []
    for item in candidates:
        key = _normalize_url(item.url)
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def _unique_urls(urls: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for url in urls:
        key = _normalize_url(url)
        if key in seen:
            continue
        seen.add(key)
        out.append(url)
    return out


def _is_transient(reason: str) -> bool:
    return reason in _TRANSIENT_REASONS or reason.startswith("http_5")


def _host_ok(url: str, official_host: str) -> bool:
    host = extract_registrable_host(url)
    if not host:
        return False
    return host == official_host or host.endswith("." + official_host)


async def list_active_organizations(session: AsyncSession) -> list[Organization]:
    result = await session.execute(
        select(Organization)
        .where(Organization.tracking_status == "active")
        .order_by(Organization.name)
    )
    return list(result.scalars().all())
