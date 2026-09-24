from __future__ import annotations

import logging
import re
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import httpx

from app.ingestion.url_validation import host_matches_official

logger = logging.getLogger("app.ingestion.homepage_links")


class _AnchorParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        for key, value in attrs:
            if key.lower() == "href" and value:
                self.hrefs.append(value.strip())


_RELEVANT_HINTS = (
    "news",
    "president",
    "leadership",
    "provost",
    "cio",
    "technology",
    "it.",
    "/it/",
    "digital",
    "online",
    "learning",
    "assessment",
    "procurement",
    "purchasing",
    "rfp",
    "bid",
    "budget",
    "finance",
    "funding",
    "strategic",
    "initiative",
    "partnership",
    "vendor",
    "contract",
    "board",
    "about",
    "research",
    "foundation",
)

# Individual dated articles are too deep for a reusable source register.
_ARTICLE_PATH = re.compile(
    r"(?:/20\d{2}/\d{2}/|/20\d{2}\d{2}\d{2}-|/news/\d{8}-)",
    re.IGNORECASE,
)


def is_reusable_source_url(url: str) -> bool:
    """Prefer section hubs over one-off article URLs."""
    parsed = urlparse(url)
    path = parsed.path or "/"
    if _ARTICLE_PATH.search(path):
        return False
    parts = [part for part in path.split("/") if part]
    lowered = path.lower()
    # News hub is fine; individual story slugs under /news/ are not reusable sources.
    if "/news/" in lowered and len(parts) >= 2:
        return False
    if len(parts) > 3:
        return False
    return True


async def collect_official_page_urls(
    *,
    root_url: str,
    official_host: str,
    user_agent: str,
    timeout_seconds: float,
    max_links: int = 40,
) -> list[str]:
    """Fetch the official homepage and collect same-domain links. Deterministic, no LLM."""
    headers = {"User-Agent": user_agent, "Accept": "text/html,application/xhtml+xml,*/*;q=0.8"}
    urls: list[str] = [root_url]
    try:
        async with httpx.AsyncClient(
            timeout=timeout_seconds,
            follow_redirects=True,
            headers=headers,
            max_redirects=5,
        ) as client:
            response = await client.get(root_url)
    except httpx.HTTPError:
        logger.info("Homepage fetch failed for link discovery")
        return urls

    if response.status_code >= 400 or not response.text:
        return urls

    final_root = str(response.url)
    if host_matches_official(urlparse(final_root).hostname, official_host):
        urls[0] = final_root

    parser = _AnchorParser()
    try:
        parser.feed(response.text)
    except Exception:
        return _unique(urls)

    ranked: list[tuple[int, str]] = []
    for href in parser.hrefs:
        absolute = urljoin(final_root, href)
        parsed = urlparse(absolute)
        if parsed.scheme not in ("http", "https"):
            continue
        if not host_matches_official(parsed.hostname, official_host):
            continue
        path = (parsed.path or "/").lower()
        if path.endswith((".pdf", ".jpg", ".png", ".gif", ".css", ".js", ".zip")):
            continue
        if not is_reusable_source_url(absolute):
            continue
        score = sum(1 for hint in _RELEVANT_HINTS if hint in absolute.lower())
        ranked.append((score, absolute))

    ranked.sort(key=lambda item: (-item[0], item[1]))
    for score, absolute in ranked:
        if score == 0 and len(urls) >= 12:
            continue
        urls.append(absolute)
        if len(urls) >= max_links:
            break

    return _unique(urls)


def guess_page_category(url: str, title: str | None = None) -> str:
    text = f"{url} {title or ''}".lower()
    rules = (
        ("procurement", ("procurement", "purchasing", "rfp", "bid", "solicitation")),
        ("leadership", ("president", "leadership", "provost", "cio", "cabinet", "board")),
        ("funding", ("budget", "finance", "funding", "grant")),
        ("assessment", ("assessment", "evaluation", "accreditation")),
        ("digital_learning", ("online", "digital-learning", "elearning", "distance")),
        ("technology", ("technology", "/it/", "cio", "digital-transformation")),
        ("partnership", ("partner", "vendor", "supplier")),
        ("strategic_initiative", ("strategic", "initiative", "charter", "vision", "about")),
    )
    for category, hints in rules:
        if any(hint in text for hint in hints):
            return category
    return "strategic_initiative"


def title_from_path(url: str) -> str | None:
    path = urlparse(url).path.strip("/")
    if not path:
        return None
    part = path.split("/")[-1].replace("-", " ").replace("_", " ")
    part = re.sub(r"\s+", " ", part).strip()
    return part.title() if part else None


def _unique(urls: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for url in urls:
        key = url.split("#", 1)[0].rstrip("/").lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(url)
    return out
