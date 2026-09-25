"""SAM.gov Get Opportunities Public API collector.

Uses only documented request parameters from DATA_SOURCES.md §2 / GSA docs.
Does not download description bodies (each download is another quota hit).
Does not invent public notice deep links while they are NEEDS VERIFICATION.
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

import httpx

from app.core.config import Settings

logger = logging.getLogger("app.ingestion.collectors.sam_gov")

SOURCE_KEY = "sam_gov"
# Verified human entry point until a public notice deep link is confirmed.
EVIDENCE_ENTRY_URL = "https://sam.gov/opportunities"
# Drop surplus property; keep documented procurement-related types.
_PTYPES = "p,o,k,r,s,a,u,i"
_STOPWORDS = frozenset(
    {
        "university",
        "college",
        "the",
        "of",
        "and",
        "at",
        "for",
        "state",
        "system",
        "campus",
        "global",
        "community",
    }
)


@dataclass(frozen=True)
class SamNotice:
    notice_id: str
    title: str
    body_text: str
    content_hash: str
    published_on: date | None
    http_status: int
    retrieved_at: datetime
    match_haystack: str


@dataclass(frozen=True)
class SamSearchResult:
    ok: bool
    notices: list[SamNotice]
    http_status: int | None
    reason: str | None
    request_counted: bool


def create_sam_client(settings: Settings) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        headers={
            "User-Agent": settings.http_user_agent,
            "Accept": "application/json",
        },
        timeout=httpx.Timeout(settings.http_timeout_seconds, connect=10.0),
        follow_redirects=True,
    )


async def search_opportunities(
    client: httpx.AsyncClient,
    settings: Settings,
    *,
    title: str | None = None,
) -> SamSearchResult:
    """One search page. Caller must enforce the application daily request cap first."""
    api_key = settings.sam_gov_api_key.strip()
    if not api_key:
        return SamSearchResult(False, [], None, "missing_api_key", False)

    posted_to = datetime.now(timezone.utc).date()
    # SAM rejects a span of exactly 365 days as "more than 1 year" (inclusive bounds).
    posted_from = posted_to - timedelta(days=364)
    params: dict[str, str | int] = {
        "api_key": api_key,
        "postedFrom": posted_from.strftime("%m/%d/%Y"),
        "postedTo": posted_to.strftime("%m/%d/%Y"),
        "limit": max(1, min(settings.sam_gov_search_limit, 1000)),
        "offset": 0,
        "ptype": _PTYPES,
    }
    if title:
        params["title"] = title

    url = settings.sam_gov_search_url.strip()
    try:
        response = await client.get(url, params=params)
    except httpx.HTTPError as exc:
        logger.warning("SAM.gov request failed: %s", type(exc).__name__)
        return SamSearchResult(False, [], None, "network_error", True)

    if response.status_code in (401, 403, 429):
        return SamSearchResult(
            False, [], response.status_code, f"http_{response.status_code}", True
        )
    if response.status_code >= 400:
        detail = f"http_{response.status_code}"
        try:
            err = response.json()
            msg = err.get("errorMessage") if isinstance(err, dict) else None
            if msg:
                detail = f"http_{response.status_code}: {msg}"
        except ValueError:
            pass
        return SamSearchResult(False, [], response.status_code, detail, True)

    try:
        payload = response.json()
    except ValueError:
        return SamSearchResult(False, [], response.status_code, "invalid_json", True)

    opportunities = payload.get("opportunitiesData") or payload.get("opportunities") or []
    if not isinstance(opportunities, list):
        opportunities = []

    retrieved_at = datetime.now(timezone.utc)
    notices: list[SamNotice] = []
    for row in opportunities:
        if not isinstance(row, dict):
            continue
        notice = _parse_notice(row, http_status=response.status_code, retrieved_at=retrieved_at)
        if notice is not None:
            notices.append(notice)

    return SamSearchResult(True, notices, response.status_code, None, True)


def organization_match_needles(organization_name: str) -> list[str]:
    """Conservative substrings used to link a notice to a tracked organization."""
    name = _collapse(organization_name)
    if not name:
        return []
    needles = [name]
    # Drop a trailing "university"/"college" once for a shorter form still unique enough.
    for suffix in (" university", " college"):
        if name.endswith(suffix) and len(name) > len(suffix) + 4:
            needles.append(name[: -len(suffix)].strip())
            break
    # Significant multi-word tokens without stopwords (length guard avoids "florida" alone).
    words = [w for w in re.split(r"\s+", name) if w and w not in _STOPWORDS]
    if len(words) >= 2:
        phrase = " ".join(words)
        if len(phrase) >= 10 and phrase not in needles:
            needles.append(phrase)
    return needles


def notice_matches_organization(notice: SamNotice, organization_name: str) -> bool:
    haystack = notice.match_haystack
    for needle in organization_match_needles(organization_name):
        if len(needle) >= 6 and needle in haystack:
            return True
    return False


def _parse_notice(
    row: dict, *, http_status: int, retrieved_at: datetime
) -> SamNotice | None:
    notice_id = str(row.get("noticeId") or "").strip()
    title = str(row.get("title") or "").strip()
    if not notice_id or not title:
        return None

    notice_type = str(row.get("type") or row.get("baseType") or "").strip()
    agency = str(row.get("fullParentPathName") or "").strip()
    naics = str(row.get("naicsCode") or "").strip()
    solicitation = str(row.get("solicitationNumber") or "").strip()
    posted = str(row.get("postedDate") or "").strip()
    deadline = str(row.get("responseDeadLine") or row.get("reponseDeadLine") or "").strip()
    award = row.get("award") if isinstance(row.get("award"), dict) else {}
    awardee = ""
    if isinstance(award, dict):
        awardee_obj = award.get("awardee")
        if isinstance(awardee_obj, dict):
            awardee = str(awardee_obj.get("name") or "").strip()
        elif isinstance(awardee_obj, str):
            awardee = awardee_obj.strip()

    lines = [
        f"Title: {title}",
        f"Notice type: {notice_type}" if notice_type else "",
        f"Posted: {posted}" if posted else "",
        f"Response deadline: {deadline}" if deadline else "",
        f"Agency path: {agency}" if agency else "",
        f"NAICS: {naics}" if naics else "",
        f"Solicitation: {solicitation}" if solicitation else "",
        f"Awardee: {awardee}" if awardee else "",
        f"Notice id: {notice_id}",
        f"Source entry: {EVIDENCE_ENTRY_URL}",
    ]
    body_text = "\n".join(line for line in lines if line)
    content_hash = hashlib.sha256(body_text.encode("utf-8")).hexdigest()
    published_on = _parse_posted_date(posted)
    haystack = _collapse(" ".join([title, agency, awardee, solicitation]))

    return SamNotice(
        notice_id=notice_id,
        title=title,
        body_text=body_text,
        content_hash=content_hash,
        published_on=published_on,
        http_status=http_status,
        retrieved_at=retrieved_at,
        match_haystack=haystack,
    )


def _parse_posted_date(value: str) -> date | None:
    if not value:
        return None
    raw = value.strip()
    for candidate, fmt in (
        (raw[:10], "%Y-%m-%d"),
        (raw[:10], "%m/%d/%Y"),
        (raw[:19], "%Y-%m-%dT%H:%M:%S"),
    ):
        try:
            return datetime.strptime(candidate, fmt).date()
        except ValueError:
            continue
    return None


def _collapse(value: str) -> str:
    return re.sub(r"\s+", " ", value.lower().replace(",", " ")).strip()
