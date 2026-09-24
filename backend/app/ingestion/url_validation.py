from __future__ import annotations

import logging
from dataclasses import dataclass
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx

logger = logging.getLogger("app.ingestion.url_validation")


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    final_url: str | None
    reason: str | None = None
    http_status: int | None = None


def extract_registrable_host(website_url: str) -> str | None:
    parsed = urlparse(website_url if "://" in website_url else f"https://{website_url}")
    host = (parsed.hostname or "").lower().strip(".")
    return host or None


def host_matches_official(host: str | None, official_host: str) -> bool:
    if not host:
        return False
    host = host.lower().strip(".")
    official = official_host.lower().strip(".")
    return host == official or host.endswith("." + official)


async def validate_candidate_url(
    *,
    candidate_url: str,
    official_host: str,
    user_agent: str,
    timeout_seconds: float,
    retries: int = 1,
) -> ValidationResult:
    try:
        parsed = urlparse(candidate_url)
    except Exception:
        return ValidationResult(False, None, "invalid_url_syntax")

    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return ValidationResult(False, None, "invalid_url_syntax")

    if not host_matches_official(parsed.hostname, official_host):
        return ValidationResult(False, None, "domain_mismatch")

    robots_allowed = await _robots_allows(
        candidate_url, user_agent=user_agent, timeout_seconds=timeout_seconds
    )
    if robots_allowed is False:
        return ValidationResult(False, None, "robots_disallow")

    headers = {"User-Agent": user_agent, "Accept": "text/html,application/xhtml+xml,*/*;q=0.8"}
    last_transient: ValidationResult | None = None
    attempts = max(1, retries + 1)
    for attempt in range(attempts):
        try:
            async with httpx.AsyncClient(
                timeout=timeout_seconds,
                follow_redirects=True,
                headers=headers,
                max_redirects=5,
            ) as client:
                response = await client.get(candidate_url)
        except httpx.TimeoutException:
            last_transient = ValidationResult(False, None, "timeout")
            continue
        except httpx.HTTPError as exc:
            logger.info("URL fetch failed", extra={"fields": {"reason": type(exc).__name__}})
            last_transient = ValidationResult(False, None, "http_failure")
            continue

        final_url = str(response.url)
        final_host = urlparse(final_url).hostname
        if not host_matches_official(final_host, official_host):
            return ValidationResult(False, None, "redirect_domain_mismatch", response.status_code)

        if response.status_code >= 500:
            last_transient = ValidationResult(
                False, final_url, f"http_{response.status_code}", response.status_code
            )
            continue

        if response.status_code >= 400:
            return ValidationResult(
                False, final_url, f"http_{response.status_code}", response.status_code
            )

        content_type = (response.headers.get("content-type") or "").lower()
        if "text/html" not in content_type and "application/xhtml" not in content_type:
            if content_type and not any(
                token in content_type for token in ("text/", "json", "xml")
            ):
                return ValidationResult(False, final_url, "not_html", response.status_code)

        body_sample = response.text[:4000].lower() if response.text else ""
        if _looks_gated(body_sample):
            return ValidationResult(False, final_url, "access_restricted", response.status_code)

        return ValidationResult(True, final_url, None, response.status_code)

    return last_transient or ValidationResult(False, None, "http_failure")


async def _robots_allows(url: str, *, user_agent: str, timeout_seconds: float) -> bool | None:
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    try:
        async with httpx.AsyncClient(timeout=timeout_seconds, follow_redirects=True) as client:
            response = await client.get(robots_url, headers={"User-Agent": user_agent})
    except httpx.HTTPError:
        return None

    if response.status_code >= 400:
        return None

    parser = RobotFileParser()
    parser.parse(response.text.splitlines())
    try:
        return bool(parser.can_fetch(user_agent, url))
    except Exception:
        return None


def _looks_gated(sample: str) -> bool:
    markers = (
        "captcha",
        "verify you are human",
        "please sign in",
        "please log in",
        "login required",
        "paywall",
        "subscribe to continue",
    )
    return any(marker in sample for marker in markers)
