from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date
from urllib.parse import urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup

_MIN_BODY_CHARS = 40
_MAX_BODY_CHARS = 60_000
_BLOCK_TAGS = ("h1", "h2", "h3", "h4", "p", "li", "blockquote", "dd", "td")
_NOISE_TAGS = (
    "script",
    "style",
    "noscript",
    "nav",
    "header",
    "footer",
    "aside",
    "form",
    "iframe",
    "svg",
    "button",
)
_DATE_META_KEYS = frozenset(
    {
        "article:published_time",
        "og:published_time",
        "datepublished",
        "pubdate",
        "publishdate",
        "dc.date",
        "dc.date.issued",
    }
)
_ISO_DATE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")


@dataclass(frozen=True)
class NormalizedPage:
    title: str | None
    body_text: str
    content_hash: str
    published_on: date | None
    links: list[str]
    content_links: list[str]


def normalize_html(html: str, base_url: str, *, allow_time_tag: bool = False) -> NormalizedPage:
    """HTML to title, text, hash, links, and a publication date only when the page states one.
    `body_text` is empty when the page has no readable text; links are still returned."""
    soup = BeautifulSoup(html, "html.parser")
    links = _absolute_links(soup, base_url)
    title = _title(soup)
    published_on = _published_on(soup, allow_time_tag=allow_time_tag)

    for tag in soup(list(_NOISE_TAGS)):
        tag.decompose()
    root = soup.find("article") or soup.find("main") or soup.body or soup
    content_links = _absolute_links(root, base_url)

    blocks: list[str] = []
    seen: set[str] = set()
    for tag in root.find_all(_BLOCK_TAGS):
        if tag.find(_BLOCK_TAGS):
            continue
        text = re.sub(r"\s+", " ", tag.get_text(" ", strip=True)).strip()
        min_len = 3 if tag.name.startswith("h") else 30
        if len(text) < min_len or text in seen:
            continue
        seen.add(text)
        blocks.append(text)

    body = "\n\n".join(blocks).strip()
    if len(body) < _MIN_BODY_CHARS:
        body = _text_lines(root)
    body = body[:_MAX_BODY_CHARS].strip()
    if len(body) < _MIN_BODY_CHARS:
        return NormalizedPage(title, "", "", published_on, links, content_links)
    return NormalizedPage(title, body, content_hash(body), published_on, links, content_links)


def _text_lines(root) -> str:
    """Fallback for pages that keep their text in plain containers instead of paragraphs."""
    lines: list[str] = []
    seen: set[str] = set()
    for raw in root.get_text("\n").splitlines():
        line = re.sub(r"\s+", " ", raw).strip()
        if len(line) < 30 or line in seen:
            continue
        seen.add(line)
        lines.append(line)
    return "\n\n".join(lines)


def content_hash(text: str) -> str:
    normalized = re.sub(r"\s+", " ", text.strip()).lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _title(soup: BeautifulSoup) -> str | None:
    for candidate in (
        soup.find("meta", attrs={"property": "og:title"}),
        soup.find("meta", attrs={"name": "twitter:title"}),
    ):
        if candidate and candidate.get("content"):
            return candidate["content"].strip()[:400] or None
    if soup.title and soup.title.get_text(strip=True):
        return soup.title.get_text(strip=True)[:400]
    h1 = soup.find("h1")
    if h1 and h1.get_text(strip=True):
        return h1.get_text(strip=True)[:400]
    return None


def _published_on(soup: BeautifulSoup, *, allow_time_tag: bool) -> date | None:
    for meta in soup.find_all("meta"):
        key = (meta.get("property") or meta.get("name") or meta.get("itemprop") or "").lower()
        if key in _DATE_META_KEYS:
            parsed = _parse_date(meta.get("content") or "")
            if parsed:
                return parsed

    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        parsed = _date_from_json_ld(script.string or "")
        if parsed:
            return parsed

    if allow_time_tag:
        time_tag = soup.find("time")
        if time_tag:
            return _parse_date(time_tag.get("datetime") or time_tag.get_text(strip=True))
    return None


def _date_from_json_ld(raw: str) -> date | None:
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
    stack = [data]
    while stack:
        item = stack.pop()
        if isinstance(item, dict):
            value = item.get("datePublished")
            if isinstance(value, str):
                parsed = _parse_date(value)
                if parsed:
                    return parsed
            stack.extend(item.values())
        elif isinstance(item, list):
            stack.extend(item)
    return None


def _parse_date(value: str) -> date | None:
    match = _ISO_DATE.search(value)
    if not match:
        return None
    try:
        return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    except ValueError:
        return None


def _absolute_links(soup, base_url: str) -> list[str]:
    links: list[str] = []
    seen: set[str] = set()
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        parts = urlsplit(urljoin(base_url, href))
        if parts.scheme not in ("http", "https"):
            continue
        absolute = urlunsplit((parts.scheme, parts.netloc, parts.path or "/", parts.query, ""))
        if absolute in seen:
            continue
        seen.add(absolute)
        links.append(absolute)
    return links
