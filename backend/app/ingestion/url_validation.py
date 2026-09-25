from __future__ import annotations

from urllib.parse import urlparse

_GATED_MARKERS = (
    "captcha",
    "verify you are human",
    "please sign in",
    "please log in",
    "login required",
    "paywall",
    "subscribe to continue",
)


def extract_registrable_host(website_url: str) -> str | None:
    parsed = urlparse(website_url if "://" in website_url else f"https://{website_url}")
    host = (parsed.hostname or "").lower().strip(".")
    if host.startswith("www."):
        host = host[4:]
    return host or None


def host_matches_official(host: str | None, official_host: str) -> bool:
    if not host:
        return False
    host = host.lower().strip(".")
    official = official_host.lower().strip(".")
    return host == official or host.endswith("." + official)


def looks_gated(html: str) -> bool:
    sample = html[:4000].lower()
    return any(marker in sample for marker in _GATED_MARKERS)
