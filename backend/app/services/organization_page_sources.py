from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import ConflictError, NotFoundError, ValidationAppError
from app.ingestion.fetcher import Fetcher, create_http_client
from app.ingestion.limiter import HostLimiter
from app.ingestion.normalizer import normalize_html
from app.ingestion.url_validation import extract_registrable_host, host_matches_official
from app.repositories.organization_sources import PAGE_CATEGORIES, OrganizationSource
from app.repositories.organizations import Organization
from app.services.organization_website import normalize_website_url

_REASON_MESSAGES = {
    "invalid_url_syntax": "Enter a valid http(s) page URL.",
    "dns_failure": "The page host could not be resolved.",
    "private_address": "Private or local network addresses are not allowed.",
    "robots_unavailable": "robots.txt could not be read for this page; try again later.",
    "robots_disallow": "Automated access to this URL is disallowed by robots.txt.",
    "timeout": "The page did not respond in time.",
    "http_failure": "The page could not be reached.",
    "access_restricted": "The page appears to require login, CAPTCHA, or a paywall.",
    "empty_page": "The page returned empty content.",
    "not_html": "The URL did not return an HTML page.",
    "domain_mismatch": "The page must stay on the organization's official website domain.",
    "redirect_domain_mismatch": "The page redirected off the organization's official domain.",
    "redirect_failure": "The page redirected in a way that could not be followed.",
    "host_rate_limited": "The host is temporarily rate-limited.",
}


async def add_organization_page_source(
    session: AsyncSession,
    organization_id: uuid.UUID,
    *,
    url: str,
    page_category: str,
    source_title: str | None,
    settings: Settings,
) -> OrganizationSource:
    if page_category not in PAGE_CATEGORIES:
        raise ValidationAppError(
            message="Choose a valid page category.",
            details={"page_category": "invalid"},
        )

    org = await session.get(Organization, organization_id)
    if org is None:
        raise NotFoundError("organization")
    official_host = extract_registrable_host(org.website_url or "")
    if not official_host:
        raise ValidationAppError(
            message="This organization has no official website to match against.",
            details={"website_url": "required"},
        )

    normalized = normalize_website_url(url)
    page_host = extract_registrable_host(normalized)
    if not page_host or not host_matches_official(page_host, official_host):
        raise ValidationAppError(
            message="The page URL must be on this organization's official website domain.",
            details={"url": "domain_mismatch"},
        )

    limiter = HostLimiter()
    async with create_http_client(settings) as client:
        fetcher = Fetcher(client, limiter, settings)
        result = await fetcher.fetch(normalized, official_host)

    if not result.ok or not result.final_url or not result.html:
        reason = result.reason or "http_failure"
        message = _REASON_MESSAGES.get(reason)
        if message is None and reason.startswith("http_"):
            message = f"The page returned HTTP {reason.removeprefix('http_')}."
        if message is None:
            message = "The page could not be verified."
        raise ValidationAppError(message=message, details={"url": reason})

    final_url = result.final_url
    title = (source_title or "").strip() or None
    if title is None:
        normalized_page = normalize_html(result.html, final_url)
        title = normalized_page.title

    existing = await session.scalar(
        select(OrganizationSource).where(
            OrganizationSource.organization_id == organization_id,
            OrganizationSource.url == final_url,
        )
    )
    now = datetime.now(timezone.utc)
    if existing is not None:
        if existing.status == "approved":
            raise ConflictError("url", "This page is already an approved source for the organization.")
        existing.status = "approved"
        existing.rejection_reason = None
        existing.page_category = page_category
        if title:
            existing.source_title = title
        existing.extraction_status = "pending"
        existing.is_official = True
        existing.last_validated_at = now
        await session.commit()
        await session.refresh(existing)
        return existing

    row = OrganizationSource(
        organization_id=organization_id,
        url=final_url,
        source_title=title,
        page_category=page_category,
        status="approved",
        extraction_status="pending",
        is_official=True,
        rejection_reason=None,
        last_validated_at=now,
    )
    session.add(row)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError("url", "This page is already an approved source for the organization.") from exc
    await session.refresh(row)
    return row


async def reject_organization_page_source(
    session: AsyncSession,
    organization_id: uuid.UUID,
    organization_source_id: uuid.UUID,
    *,
    rejection_reason: str | None,
) -> OrganizationSource:
    org = await session.get(Organization, organization_id)
    if org is None:
        raise NotFoundError("organization")

    row = await session.get(OrganizationSource, organization_source_id)
    if row is None or row.organization_id != organization_id:
        raise NotFoundError("organization_source")

    row.status = "rejected"
    row.rejection_reason = (rejection_reason or "").strip() or "Rejected by sales manager"
    row.last_validated_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(row)
    return row
