from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from app.core.config import Settings
from app.core.errors import ValidationAppError
from app.ingestion.fetcher import Fetcher, create_http_client
from app.ingestion.limiter import HostLimiter
from app.ingestion.url_validation import extract_registrable_host

_REASON_MESSAGES = {
    "invalid_url_syntax": "Enter a valid http(s) website URL.",
    "dns_failure": "The website host could not be resolved.",
    "private_address": "Private or local network addresses are not allowed.",
    "robots_unavailable": "robots.txt could not be read for this site; try again later.",
    "robots_disallow": "Automated access to this URL is disallowed by robots.txt.",
    "timeout": "The website did not respond in time.",
    "http_failure": "The website could not be reached.",
    "access_restricted": "The website appears to require login, CAPTCHA, or a paywall.",
    "empty_page": "The website returned an empty page.",
    "not_html": "The website did not return an HTML page.",
    "domain_mismatch": "The website URL host is not valid.",
    "redirect_domain_mismatch": "The website redirected to a different domain.",
    "redirect_failure": "The website redirected in a way that could not be followed.",
    "host_rate_limited": "The website is temporarily rate-limited.",
}


@dataclass(frozen=True)
class WebsiteValidationResult:
    final_url: str
    host: str


def normalize_website_url(raw: str) -> str:
    value = raw.strip()
    if not value:
        raise ValidationAppError(
            message="Website URL is required.",
            details={"website_url": "required"},
        )
    if "://" not in value:
        value = f"https://{value}"
    parsed = urlparse(value)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValidationAppError(
            message="Enter a valid website URL.",
            details={"website_url": "invalid"},
        )
    # Prefer a stable homepage form: scheme + host + path (default /)
    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/") or "/"
    normalized = f"{parsed.scheme.lower()}://{parsed.netloc.lower()}{path}"
    if parsed.query:
        normalized = f"{normalized}?{parsed.query}"
    return normalized


async def validate_official_website(url: str, settings: Settings) -> WebsiteValidationResult:
    normalized = normalize_website_url(url)
    host = extract_registrable_host(normalized)
    if not host:
        raise ValidationAppError(
            message="Enter a valid website URL.",
            details={"website_url": "invalid"},
        )

    limiter = HostLimiter()
    async with create_http_client(settings) as client:
        fetcher = Fetcher(client, limiter, settings)
        result = await fetcher.fetch(normalized, host)

    if not result.ok or not result.final_url:
        reason = result.reason or "http_failure"
        message = _REASON_MESSAGES.get(reason)
        if message is None and reason.startswith("http_"):
            message = f"The website returned HTTP {reason.removeprefix('http_')}."
        if message is None:
            message = "The website could not be verified."
        raise ValidationAppError(
            message=message,
            details={"website_url": reason},
        )

    final = result.final_url
    # Prefer https final when the redirect chain ends on https
    final_host = extract_registrable_host(final)
    if not final_host:
        raise ValidationAppError(
            message="The website could not be verified.",
            details={"website_url": "invalid"},
        )
    return WebsiteValidationResult(final_url=final, host=final_host)
