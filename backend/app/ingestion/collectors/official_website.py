from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import date, datetime

from app.ingestion.fetcher import Fetcher, FetchResult
from app.ingestion.homepage_links import select_article_links
from app.ingestion.normalizer import normalize_html


@dataclass(frozen=True)
class CollectedDocument:
    url: str
    title: str | None
    body_text: str
    content_hash: str
    published_on: date | None
    http_status: int | None
    retrieved_at: datetime


@dataclass
class PageCollection:
    page_ok: bool
    reason: str | None = None
    documents: list[CollectedDocument] = field(default_factory=list)
    articles_found: int = 0
    articles_failed: int = 0


async def collect_page(
    fetcher: Fetcher,
    *,
    fetched: FetchResult,
    page_category: str,
    official_host: str,
    article_limit: int,
) -> PageCollection:
    """Turn an already-fetched approved page into documents. A news hub also yields up to
    `article_limit` article pages that the hub itself links to on the same host."""
    if not fetched.ok or not fetched.html or not fetched.final_url or not fetched.retrieved_at:
        return PageCollection(False, fetched.reason or "fetch_failed")

    page = await asyncio.to_thread(normalize_html, fetched.html, fetched.final_url)
    result = PageCollection(True)
    if page.body_text:
        result.documents.append(
            CollectedDocument(
                url=fetched.final_url,
                title=page.title,
                body_text=page.body_text,
                content_hash=page.content_hash,
                published_on=page.published_on if page_category != "news" else None,
                http_status=fetched.http_status,
                retrieved_at=fetched.retrieved_at,
            )
        )

    if page_category == "news":
        article_urls = select_article_links(
            [*page.content_links, *page.links],
            hub_url=fetched.final_url,
            official_host=official_host,
            limit=article_limit,
        )
        result.articles_found = len(article_urls)
        articles = await asyncio.gather(
            *[_collect_article(fetcher, url, official_host) for url in article_urls]
        )
        for article in articles:
            if article is None:
                result.articles_failed += 1
            else:
                result.documents.append(article)

    if not result.documents:
        result.page_ok = False
        result.reason = "no_article_links" if page_category == "news" and not page.body_text else "no_readable_text"
    return result


async def _collect_article(fetcher: Fetcher, url: str, official_host: str) -> CollectedDocument | None:
    fetched = await fetcher.fetch(url, official_host)
    if not fetched.ok or not fetched.html or not fetched.final_url or not fetched.retrieved_at:
        return None
    page = await asyncio.to_thread(
        normalize_html, fetched.html, fetched.final_url, allow_time_tag=True
    )
    if not page.body_text:
        return None
    return CollectedDocument(
        url=fetched.final_url,
        title=page.title,
        body_text=page.body_text,
        content_hash=page.content_hash,
        published_on=page.published_on,
        http_status=fetched.http_status,
        retrieved_at=fetched.retrieved_at,
    )
