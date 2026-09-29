"""USAspending.gov API v2 collector (DATA_SOURCES.md §3).

Resolves a tracked organization to one recipient via autocomplete. Ambiguous or
weak matches store nothing. Award rows become documents with the verified site
root as evidence URL (deep links remain NEEDS VERIFICATION).
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

import httpx

from app.core.config import Settings

logger = logging.getLogger("app.ingestion.collectors.usaspending")

SOURCE_KEY = "usaspending"
EVIDENCE_ENTRY_URL = "https://www.usaspending.gov"
API_ROOT = "https://api.usaspending.gov"

# One group per spending_by_award call (API rejects mixed groups).
_CONTRACT_TYPES = ("A", "B", "C", "D")
_GRANT_TYPES = ("02", "03", "04", "05")

_BLOCKING_EXTRA = (
    " FOUNDATION",
    " RESEARCH FOUNDATION",
    " BOARD OF TRUSTEES",
)


@dataclass(frozen=True)
class UsaAward:
    award_id: str
    external_id: str
    title: str
    body_text: str
    content_hash: str
    published_on: date | None
    recipient_name: str
    http_status: int
    retrieved_at: datetime


@dataclass(frozen=True)
class UsaRecipientResolve:
    ok: bool
    recipient_name: str | None
    candidates: list[str]
    reason: str | None
    http_status: int | None
    request_counted: bool


@dataclass(frozen=True)
class UsaAwardsResult:
    ok: bool
    awards: list[UsaAward]
    reason: str | None
    http_status: int | None
    request_counted: bool


def create_usa_client(settings: Settings) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=API_ROOT,
        headers={
            "User-Agent": settings.http_user_agent,
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        timeout=httpx.Timeout(settings.http_timeout_seconds, connect=10.0),
        follow_redirects=True,
    )


def _norm(value: str) -> str:
    text = value.upper().strip()
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def recipient_compatible(organization_name: str, recipient_name: str) -> bool:
    """Accept only a clear name match for the tracked organization."""
    org = _norm(organization_name)
    recipient = _norm(recipient_name)
    if not org or not recipient:
        return False
    if org == recipient:
        return True
    if recipient.startswith(org + " "):
        for blocker in _BLOCKING_EXTRA:
            if blocker in f" {recipient}" and blocker.strip() not in org:
                return False
        return True
    return False


async def resolve_recipient(
    client: httpx.AsyncClient,
    *,
    organization_name: str,
) -> UsaRecipientResolve:
    try:
        response = await client.post(
            "/api/v2/autocomplete/recipient/",
            json={"search_text": organization_name.strip()},
        )
    except httpx.HTTPError as exc:
        logger.warning("USAspending autocomplete failed: %s", exc)
        return UsaRecipientResolve(False, None, [], "network_error", None, True)

    if response.status_code != 200:
        return UsaRecipientResolve(
            False,
            None,
            [],
            f"http_{response.status_code}",
            response.status_code,
            True,
        )

    payload = response.json() if response.content else {}
    results = payload.get("results") if isinstance(payload, dict) else None
    if not isinstance(results, list):
        return UsaRecipientResolve(False, None, [], "malformed", response.status_code, True)

    names = [
        str(row.get("recipient_name")).strip()
        for row in results
        if isinstance(row, dict) and row.get("recipient_name")
    ]
    if len(names) == 0:
        return UsaRecipientResolve(True, None, [], "no_recipient", response.status_code, True)
    if len(names) != 1:
        return UsaRecipientResolve(
            True,
            None,
            names,
            "ambiguous_recipient",
            response.status_code,
            True,
        )
    if not recipient_compatible(organization_name, names[0]):
        return UsaRecipientResolve(
            True,
            None,
            names,
            "recipient_name_mismatch",
            response.status_code,
            True,
        )
    return UsaRecipientResolve(True, names[0], names, None, response.status_code, True)


async def search_awards_for_recipient(
    client: httpx.AsyncClient,
    *,
    recipient_name: str,
    max_awards: int,
    lookback_years: int = 3,
) -> UsaAwardsResult:
    """Contracts then grants. Filters to the exact resolved recipient name."""
    end = datetime.now(timezone.utc).date()
    start = date(end.year - lookback_years, 1, 1)
    retrieved_at = datetime.now(timezone.utc)
    awards: list[UsaAward] = []
    last_status: int | None = None
    counted = False
    per_group = max(1, (max_awards + 1) // 2)

    for type_codes in (_CONTRACT_TYPES, _GRANT_TYPES):
        if len(awards) >= max_awards:
            break
        result = await _spending_by_award(
            client,
            recipient_name=recipient_name,
            award_type_codes=list(type_codes),
            start=start,
            end=end,
            limit=per_group,
            retrieved_at=retrieved_at,
        )
        counted = counted or result.request_counted
        last_status = result.http_status
        if not result.ok:
            # Soft: keep whatever we already have; report failure only if empty.
            if not awards:
                return result
            continue
        for award in result.awards:
            if len(awards) >= max_awards:
                break
            awards.append(award)

    return UsaAwardsResult(True, awards, None, last_status, counted)


async def _spending_by_award(
    client: httpx.AsyncClient,
    *,
    recipient_name: str,
    award_type_codes: list[str],
    start: date,
    end: date,
    limit: int,
    retrieved_at: datetime,
) -> UsaAwardsResult:
    body = {
        "filters": {
            "recipient_search_text": [recipient_name],
            "time_period": [
                {"start_date": start.isoformat(), "end_date": end.isoformat()}
            ],
            "award_type_codes": award_type_codes,
        },
        "fields": [
            "Award ID",
            "Recipient Name",
            "Award Amount",
            "Description",
            "Start Date",
            "End Date",
            "Awarding Agency",
            "Award Type",
            "generated_internal_id",
        ],
        "limit": limit,
        "page": 1,
        "sort": "Award Amount",
        "order": "desc",
    }
    try:
        response = await client.post("/api/v2/search/spending_by_award/", json=body)
    except httpx.HTTPError as exc:
        logger.warning("USAspending spending_by_award failed: %s", exc)
        return UsaAwardsResult(False, [], "network_error", None, True)

    if response.status_code != 200:
        return UsaAwardsResult(
            False,
            [],
            f"http_{response.status_code}",
            response.status_code,
            True,
        )

    payload = response.json() if response.content else {}
    rows = payload.get("results") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        return UsaAwardsResult(False, [], "malformed", response.status_code, True)

    want = _norm(recipient_name)
    awards: list[UsaAward] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        row_recipient = str(row.get("Recipient Name") or "").strip()
        if _norm(row_recipient) != want:
            # recipient_search_text can surface near names; keep exact match only.
            continue
        award = _award_from_row(row, http_status=response.status_code, retrieved_at=retrieved_at)
        if award is not None:
            awards.append(award)

    return UsaAwardsResult(True, awards, None, response.status_code, True)


def _award_from_row(
    row: dict, *, http_status: int, retrieved_at: datetime
) -> UsaAward | None:
    award_id = str(row.get("Award ID") or "").strip()
    generated = str(row.get("generated_internal_id") or "").strip()
    external_id = generated or award_id
    if not external_id:
        return None

    recipient = str(row.get("Recipient Name") or "").strip()
    agency = str(row.get("Awarding Agency") or "").strip()
    award_type = str(row.get("Award Type") or "").strip()
    description = str(row.get("Description") or "").strip()
    amount = row.get("Award Amount")
    start = str(row.get("Start Date") or "").strip()
    end = str(row.get("End Date") or "").strip()

    title = description[:200] if description else (award_id or external_id)
    lines = [
        "Source: USAspending.gov",
        f"Award ID: {award_id or external_id}",
        f"Recipient: {recipient}" if recipient else None,
        f"Awarding agency: {agency}" if agency else None,
        f"Award type: {award_type}" if award_type else None,
        f"Award amount: {amount}" if amount is not None else None,
        f"Start date: {start}" if start else "Start date: unavailable",
        f"End date: {end}" if end else "End date: unavailable",
        f"Description: {description}" if description else None,
        # Deep award URLs are NEEDS VERIFICATION in DATA_SOURCES.md §3.3.
        f"Evidence entry: {EVIDENCE_ENTRY_URL}",
        f"Internal award key: {external_id}",
    ]
    body_text = "\n".join(line for line in lines if line)
    content_hash = hashlib.sha256(body_text.encode("utf-8")).hexdigest()
    published_on = _parse_date(start) or _parse_date(end)

    return UsaAward(
        award_id=award_id or external_id,
        external_id=external_id,
        title=title,
        body_text=body_text,
        content_hash=content_hash,
        published_on=published_on,
        recipient_name=recipient,
        http_status=http_status,
        retrieved_at=retrieved_at,
    )


def _parse_date(value: str) -> date | None:
    if not value or len(value) < 10:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None
