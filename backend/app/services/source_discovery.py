from __future__ import annotations

import logging
from datetime import datetime, timezone
from urllib.parse import urlsplit, urlunsplit

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.ai.adapters.base import LLMProviderAdapter, SourceCandidate
from app.core.config import Settings
from app.ingestion.homepage_links import (
    collect_official_page_urls,
    guess_page_category,
    is_reusable_source_url,
    title_from_path,
)
from app.ingestion.url_validation import extract_registrable_host, validate_candidate_url
from app.repositories.organization_sources import OrganizationSource
from app.repositories.organizations import Organization
from app.repositories.scans import ScanRun

logger = logging.getLogger("app.services.source_discovery")

_TRANSIENT_REASONS = frozenset({"timeout", "http_failure", "http_500", "http_502", "http_503", "http_504"})


async def run_organization_discovery(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    settings: Settings,
    llm: LLMProviderAdapter,
    scan_id,
    organization_id,
) -> None:
    async with session_factory() as session:
        scan = await session.get(ScanRun, scan_id)
        org = await session.get(Organization, organization_id)
        if scan is None or org is None:
            return

        scan.status = "running"
        scan.stage = "discovering"
        scan.started_at = datetime.now(timezone.utc)
        scan.error_detail = None
        await session.commit()

        official_host = extract_registrable_host(org.website_url or "")
        if not official_host:
            await _fail(session, scan, "Organization has no official website_url")
            return

        root_url = (
            org.website_url
            if org.website_url and "://" in org.website_url
            else f"https://{official_host}"
        )

        # 1) Deterministic candidates from the official homepage (no invented URLs).
        discovered_urls = await collect_official_page_urls(
            root_url=root_url,
            official_host=official_host,
            user_agent=settings.http_user_agent,
            timeout_seconds=settings.url_validation_timeout_seconds,
        )

        # 2) Keep previously approved URLs in the candidate set for stable re-scans.
        existing_approved = (
            await session.execute(
                select(OrganizationSource).where(
                    OrganizationSource.organization_id == organization_id,
                    OrganizationSource.status == "approved",
                )
            )
        ).scalars().all()
        for row in existing_approved:
            discovered_urls.append(row.url)

        discovered_urls = [
            url for url in _unique_urls(discovered_urls) if is_reusable_source_url(url)
        ]
        if root_url not in discovered_urls:
            discovered_urls.insert(0, root_url)

        await _collapse_url_aliases(session, organization_id=organization_id)
        await session.commit()

        # Refresh approved after alias collapse.
        existing_approved = (
            await session.execute(
                select(OrganizationSource).where(
                    OrganizationSource.organization_id == organization_id,
                    OrganizationSource.status == "approved",
                )
            )
        ).scalars().all()

        # 3) LLM may only select/classify from that allowlist (anti-hallucination).
        try:
            selected = await llm.propose_organization_urls(
                organization_name=org.name,
                official_domain=official_host,
                candidate_urls=discovered_urls,
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
                for url in discovered_urls[:8]
            ]

        # Always validate the official root.
        candidates = _dedupe_candidates(
            [
                SourceCandidate(
                    url=root_url,
                    title=f"{org.name} official site",
                    page_category="strategic_initiative",
                    reason="Official domain root from organization record",
                ),
                *[item for item in selected if is_reusable_source_url(item.url)],
            ]
        )

        scan.candidates_found = len(candidates)
        scan.stage = "validating_sources"
        scan.sources = []
        await session.commit()

        approved = 0
        rejected = 0
        source_rows: list[dict] = []
        existing_by_url = {
            _normalize_url(row.url): row for row in existing_approved
        }

        for candidate in candidates:
            result = await validate_candidate_url(
                candidate_url=candidate.url,
                official_host=official_host,
                user_agent=settings.http_user_agent,
                timeout_seconds=settings.url_validation_timeout_seconds,
                retries=1,
            )
            if result.ok and result.final_url:
                final_norm = _normalize_url(result.final_url)
                await _upsert_source(
                    session,
                    organization_id=organization_id,
                    url=final_norm,
                    title=candidate.title,
                    page_category=candidate.page_category,
                    status="approved",
                    is_official=True,
                    rejection_reason=None,
                )
                approved += 1
                source_rows.append(
                    {
                        "source_name": candidate.title or final_norm,
                        "status": "succeeded",
                        "detail": candidate.page_category,
                    }
                )
            else:
                reason = result.reason or "validation_failed"
                prior = existing_by_url.get(_normalize_url(candidate.url))
                if prior is None and result.final_url:
                    prior = existing_by_url.get(_normalize_url(result.final_url))

                # Do not demote a previously approved URL on transient network errors.
                if prior is not None and _is_transient(reason):
                    source_rows.append(
                        {
                            "source_name": prior.source_title or prior.url,
                            "status": "succeeded",
                            "detail": "kept_previous_approved_transient_error",
                        }
                    )
                    approved += 1
                else:
                    rejected += 1
                    if result.final_url and _host_ok(result.final_url, official_host):
                        # Hard failure only — never overwrite approved with rejected on soft errors.
                        if prior is None or not _is_transient(reason):
                            await _upsert_source(
                                session,
                                organization_id=organization_id,
                                url=_normalize_url(result.final_url),
                                title=candidate.title,
                                page_category=candidate.page_category,
                                status="rejected",
                                is_official=True,
                                rejection_reason=reason,
                            )
                    source_rows.append(
                        {
                            "source_name": candidate.title or candidate.url,
                            "status": "failed",
                            "detail": reason,
                        }
                    )
            await session.commit()

        scan.stage = "saving_sources"
        scan.sources = source_rows
        scan.sources_approved = approved
        scan.sources_rejected = rejected
        scan.status = "succeeded" if approved > 0 else "partial" if rejected > 0 else "failed"
        if approved == 0 and rejected == 0:
            scan.status = "failed"
            scan.error_detail = "No candidates to validate"
        scan.stage = None
        scan.finished_at = datetime.now(timezone.utc)
        await session.commit()


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
    is_official: bool,
    rejection_reason: str | None,
) -> None:
    now = datetime.now(timezone.utc)
    normalized = _normalize_url(url)
    # Remove www / trailing-slash aliases so unique(org, url) stays one row per page.
    aliases = _alias_urls(normalized)
    if aliases:
        await session.execute(
            delete(OrganizationSource).where(
                OrganizationSource.organization_id == organization_id,
                OrganizationSource.url.in_(aliases),
                OrganizationSource.url != normalized,
            )
        )
    statement = (
        insert(OrganizationSource)
        .values(
            organization_id=organization_id,
            url=normalized,
            source_title=title,
            page_category=page_category,
            status=status,
            is_official=is_official,
            rejection_reason=rejection_reason,
            last_validated_at=now,
        )
        .on_conflict_do_update(
            constraint="organization_sources_organization_id_url_key",
            set_={
                "source_title": title,
                "page_category": page_category,
                "status": status,
                "is_official": is_official,
                "rejection_reason": rejection_reason,
                "last_validated_at": now,
                "updated_at": now,
            },
        )
    )
    await session.execute(statement)


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
        # Keep approved over rejected; otherwise keep newest validation.
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

    for key, row in best.items():
        if row.url != key:
            row.url = key


def _alias_urls(normalized: str) -> list[str]:
    parts = urlsplit(normalized)
    host = parts.netloc
    aliases = {
        normalized,
        urlunsplit((parts.scheme, f"www.{host}", parts.path, "", "")),
        urlunsplit((parts.scheme, host, parts.path.rstrip("/") or "/", "", "")),
        urlunsplit((parts.scheme, f"www.{host}", parts.path.rstrip("/") or "/", "", "")),
        urlunsplit((parts.scheme, host, parts.path + ("/" if parts.path != "/" else ""), "", "")),
        urlunsplit(
            (parts.scheme, f"www.{host}", parts.path + ("/" if parts.path != "/" else ""), "", "")
        ),
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
    if reason in _TRANSIENT_REASONS:
        return True
    return reason.startswith("http_5")


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
