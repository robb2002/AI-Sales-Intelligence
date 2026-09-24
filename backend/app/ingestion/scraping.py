import asyncio
import hashlib
import ipaddress
import logging
import re
import socket
from datetime import datetime, timezone
from typing import Any, AsyncGenerator
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from curl_cffi.requests import AsyncSession as CurlCffiAsyncSession

from app.core.config import Settings
from app.ingestion.url_validation import extract_registrable_host

logger = logging.getLogger("app.ingestion.scraping")

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "sec-ch-ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}

BOT_BLOCK_STATUS_CODES = frozenset({403, 429, 503})


def generate_content_hash(content: str) -> str:
    normalized = re.sub(r"\s+", " ", content.strip()).lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def clean_text(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[^\x09\x0A\x0D\x20-\x7E\u00A0-\uFFFF]", "", text)
    return text.strip()


def extract_from_html(html: str, url: str = "") -> dict[str, Any]:
    """Extract title, date, and clean body text from raw HTML."""
    soup = BeautifulSoup(html, "html.parser")

    # Title
    title = ""
    if soup.title:
        title = soup.title.get_text(strip=True)[:400]
    if not title:
        h1 = soup.find("h1")
        if h1:
            title = h1.get_text(strip=True)[:400]

    # Published date
    published_date = ""
    for meta in soup.find_all("meta"):
        prop = (meta.get("property") or meta.get("name") or "").lower()
        if prop in (
            "article:published_time",
            "og:published_time",
            "pubdate",
            "date",
            "dc.date",
            "datepublished",
        ):
            val = meta.get("content", "")
            if val:
                published_date = val[:30]
                break
    if not published_date:
        t = soup.find("time")
        if t:
            published_date = (t.get("datetime") or t.get_text(strip=True))[:30]
    if not published_date:
        published_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Remove noise
    for tag in soup(
        [
            "script",
            "style",
            "nav",
            "header",
            "footer",
            "aside",
            "form",
            "noscript",
            "iframe",
            "svg",
            "button",
            "input",
            "select",
            "meta",
            "link",
        ]
    ):
        tag.decompose()

    # Try trafilatura first
    content = ""
    try:
        import trafilatura

        result = trafilatura.extract(
            html, include_comments=False, include_tables=True, favor_precision=True, url=url
        )
        if result:
            content = result
    except Exception:
        pass

    # BS4 fallback
    if not content or len(content.strip()) < 80:
        paragraphs = []
        for tag in soup.find_all(["p", "li", "h1", "h2", "h3", "h4", "td", "dd", "blockquote"]):
            t = tag.get_text(separator=" ", strip=True)
            if t and len(t) > 30:
                paragraphs.append(t)
        content = "\n\n".join(paragraphs)

    if not content or len(content.strip()) < 40:
        return {
            "success": False,
            "title": title,
            "published_date": published_date,
            "content": "",
            "content_hash": "",
        }

    content = clean_text(content)[:60000]
    return {
        "success": True,
        "title": title,
        "published_date": published_date,
        "content": content,
        "content_hash": generate_content_hash(content),
    }


async def resolve_unsafe_reason(url: str) -> str | None:
    """Returns a reason string if the URL must not be fetched (SSRF guard), else None."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return f"Unsupported URL scheme: {parsed.scheme or '(none)'}"
    host = parsed.hostname
    if not host:
        return "URL is missing a host"
    try:
        infos = await asyncio.to_thread(socket.getaddrinfo, host, None)
    except socket.gaierror as e:
        return f"DNS resolution failed: {e}"
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            return f"Refusing to fetch unsafe/internal address: {ip}"
    return None


async def _fetch_with_httpx(url: str, timeout_seconds: float) -> dict[str, Any]:
    timeout = httpx.Timeout(timeout_seconds, connect=10.0)
    async with httpx.AsyncClient(
        timeout=timeout, follow_redirects=True, headers=DEFAULT_HEADERS, verify=True
    ) as client:
        resp = await client.get(url)
        return {
            "status_code": resp.status_code,
            "content_type": resp.headers.get("content-type", ""),
            "text": resp.text,
            "url": str(resp.url),
        }


async def _fetch_with_curl_cffi(url: str, timeout_seconds: float) -> dict[str, Any]:
    async with CurlCffiAsyncSession() as session:
        resp = await session.get(
            url, impersonate="chrome124", timeout=timeout_seconds, allow_redirects=True, verify=True
        )
        return {
            "status_code": resp.status_code,
            "content_type": resp.headers.get("content-type", ""),
            "text": resp.text,
            "url": str(resp.url),
        }


async def fetch_url(url: str, semaphore: asyncio.Semaphore, settings: Settings) -> dict[str, Any]:
    """Async HTTP fetch + extract, guarded against SSRF and bounded by concurrency."""
    unsafe_reason = await resolve_unsafe_reason(url)
    if unsafe_reason:
        logger.warning("Blocked %s: %s", url, unsafe_reason)
        return {"success": False, "error": unsafe_reason, "url": url}

    async with semaphore:
        logger.info("Fetching: %s", url)
        resp = None
        fetch_error = None
        try:
            resp = await _fetch_with_httpx(url, settings.url_validation_timeout_seconds)
        except httpx.TimeoutException:
            fetch_error = "Timeout"
        except Exception as e:
            fetch_error = str(e)

        if resp is None or resp["status_code"] in BOT_BLOCK_STATUS_CODES:
            logger.info(
                "httpx fetch %s for %s — retrying with browser-fingerprinted client",
                fetch_error or f"got HTTP {resp['status_code']}",
                url,
            )
            try:
                resp = await _fetch_with_curl_cffi(url, settings.url_validation_timeout_seconds)
                fetch_error = None
            except Exception as e:
                logger.warning("curl_cffi fallback failed for %s: %s", url, e)
                if resp is None:
                    fetch_error = fetch_error or str(e)

        if resp is None:
            return {"success": False, "error": fetch_error or "Unknown fetch error", "url": url}
        if resp["status_code"] >= 400:
            return {"success": False, "error": f"HTTP {resp['status_code']}", "url": url}
        ct = (resp["content_type"] or "").lower()
        if "text/html" not in ct and "xhtml" not in ct:
            return {"success": False, "error": f"Non-HTML content: {ct}", "url": url}

        extracted = await asyncio.to_thread(extract_from_html, resp["text"], resp["url"])
        extracted["url"] = resp["url"]
        extracted["status_code"] = resp["status_code"]
        extracted["success"] = True
        return extracted


async def save_document(
    session,
    organization_id,
    url: str,
    extracted: dict[str, Any],
) -> None:
    from app.repositories.documents import Document
    from app.repositories.sources import Source
    from sqlalchemy import select

    # We need a source_id for this. If it's an official website, there might be a source with source_key="website:<organization_id>"
    source_key = f"website:{organization_id}"
    source = await session.scalar(select(Source).where(Source.source_key == source_key))
    if not source:
        source = Source(
            source_key=source_key,
            name="Official Website",
            official_url=url,
            source_kind="official_website",
            reliability_label="official_website",
        )
        session.add(source)
        await session.flush()

    doc = Document(
        source_id=source.source_id,
        organization_id=organization_id,
        source_url=url,
        title=extracted.get("title", ""),
        body_text=extracted.get("content", ""),
        content_hash=extracted.get("content_hash", ""),
        published_on=None,  # Or parse the published_date string
        http_status=extracted.get("status_code", 200),
        data_origin="live",
        retrieved_at=datetime.now(timezone.utc),
    )
    session.add(doc)
    await session.commit()


async def run_scraping_pipeline(
    session_factory,
    scan_id,
    organization_id,
    urls: list[str],
    settings: Settings,
) -> None:
    from sqlalchemy import update
    from app.repositories.organization_sources import OrganizationSource
    from app.repositories.scans import ScanRun

    semaphore = asyncio.Semaphore(settings.scan_org_concurrency)

    async def _update_status(url: str, status: str) -> None:
        async with session_factory() as session:
            await session.execute(
                update(OrganizationSource)
                .where(
                    OrganizationSource.organization_id == organization_id,
                    OrganizationSource.url == url,
                )
                .values(extraction_status=status)
            )
            await session.commit()

    async def _process_url(url: str) -> bool:
        await _update_status(url, "extracting")
        extracted = await fetch_url(url, semaphore, settings)
        if not extracted.get("success") or not extracted.get("content"):
            err = extracted.get("error", "No content extracted")
            logger.warning("FAILED %s: %s", url, err)
            await _update_status(url, "failed")
            return False

        try:
            async with session_factory() as session:
                await save_document(session, organization_id, url, extracted)
            await _update_status(url, "extracted")
            return True
        except Exception as e:
            logger.exception("Failed to save %s", url)
            await _update_status(url, "failed")
            return False

    try:
        tasks = [_process_url(url) for url in urls]
        results = await asyncio.gather(*tasks)
        successes = sum(1 for r in results if r)
        failures = len(urls) - successes
        
        async with session_factory() as session:
            scan = await session.get(ScanRun, scan_id)
            if scan:
                scan.stage = None
                scan.status = "succeeded" if successes > 0 and failures == 0 else "partial" if successes > 0 else "failed"
                scan.finished_at = datetime.now(timezone.utc)
                await session.commit()
    except Exception as e:
        logger.exception("Pipeline error")
        async with session_factory() as session:
            scan = await session.get(ScanRun, scan_id)
            if scan:
                scan.stage = None
                scan.status = "failed"
                scan.error_detail = f"Scraping pipeline failed: {str(e)}"
                scan.finished_at = datetime.now(timezone.utc)
                await session.commit()
