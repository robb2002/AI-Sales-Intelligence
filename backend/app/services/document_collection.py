from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.ingestion.collectors.official_website import PageCollection, collect_page
from app.ingestion.fetcher import Fetcher
from app.ingestion.url_validation import extract_registrable_host
from app.repositories import documents as documents_repo
from app.repositories import organization_sources as organization_sources_repo
from app.repositories.organizations import Organization
from app.repositories.scans import ScanRun
from app.services.source_discovery import ApprovedPage

logger = logging.getLogger("app.services.document_collection")


@dataclass
class WebsiteCollectionResult:
    changed: int
    failed_pages: int
    attempted_pages: int
    reused_pages: int
    source_rows: list[dict]
    changed_document_ids: list[UUID] = field(default_factory=list)


async def collect_organization_documents(
    session: AsyncSession,
    *,
    settings: Settings,
    fetcher: Fetcher,
    scan: ScanRun,
    org: Organization,
    pages: list[ApprovedPage],
) -> WebsiteCollectionResult:
    """Store documents for one organization's approved pages. Does not set terminal
    scan status — the orchestrator merges SAM.gov and website outcomes."""
    official_host = extract_registrable_host(org.website_url or "") or ""
    to_collect = [page for page in pages if page.fetched is not None]
    reused = len(pages) - len(to_collect)

    scan.stage = "extracting"
    await organization_sources_repo.set_extraction_status(
        session, [page.organization_source_id for page in to_collect], "extracting"
    )
    await session.commit()

    write_lock = asyncio.Lock()
    source_rows: list[dict] = []
    changed_total = 0
    failed_pages = 0
    changed_document_ids: list[UUID] = []

    async def collect_one(page: ApprovedPage) -> None:
        nonlocal changed_total, failed_pages
        try:
            outcome = await collect_page(
                fetcher,
                fetched=page.fetched,  # type: ignore[arg-type]
                page_category=page.page_category,
                official_host=official_host,
                article_limit=settings.scan_news_articles_per_hub,
            )
        except Exception:
            logger.exception("Page collection failed")
            outcome = PageCollection(False, "collection_error")

        async with write_lock:
            counts = {"inserted": 0, "updated": 0, "unchanged": 0}
            for document in outcome.documents:
                status, document_id = await documents_repo.save_current_document(
                    session,
                    organization_id=org.organization_id,
                    organization_source_id=page.organization_source_id,
                    source_url=document.url,
                    title=document.title,
                    body_text=document.body_text,
                    content_hash=document.content_hash,
                    published_on=document.published_on,
                    http_status=document.http_status,
                    retrieved_at=document.retrieved_at,
                )
                counts[status] += 1
                if status in ("inserted", "updated"):
                    changed_document_ids.append(document_id)
            await organization_sources_repo.set_extraction_status(
                session,
                [page.organization_source_id],
                "extracted" if outcome.page_ok else "failed",
            )
            changed_total += counts["inserted"] + counts["updated"]
            if not outcome.page_ok:
                failed_pages += 1
            source_rows.append(_result_row(page, outcome, counts))
            scan.documents_collected = int(scan.documents_collected or 0) + (
                counts["inserted"] + counts["updated"]
            )
            # Preserve SAM.gov rows already recorded on the scan.
            prior = [
                row
                for row in (scan.sources or [])
                if isinstance(row, dict) and row.get("source_name") == "SAM.gov"
            ]
            scan.sources = prior + list(source_rows)
            await session.commit()

    if to_collect:
        await asyncio.gather(*[collect_one(page) for page in to_collect])
    else:
        await session.commit()

    return WebsiteCollectionResult(
        changed=changed_total,
        failed_pages=failed_pages,
        attempted_pages=len(to_collect),
        reused_pages=reused,
        source_rows=source_rows,
        changed_document_ids=changed_document_ids,
    )


def _result_row(page: ApprovedPage, outcome: PageCollection, counts: dict[str, int]) -> dict:
    name = page.title or page.url
    if not outcome.page_ok:
        return {"source_name": name, "status": "failed", "detail": f"collection: {outcome.reason}"}
    detail = f"{counts['inserted']} new, {counts['updated']} updated, {counts['unchanged']} unchanged"
    if outcome.articles_found:
        detail += (
            f"; {outcome.articles_found - outcome.articles_failed} of "
            f"{outcome.articles_found} news articles"
        )
    return {"source_name": name, "status": "succeeded", "detail": detail}
