"""Signal deduplication (M6) — deterministic tiers only. No LLM.

AI_RAG_DESIGN.md §6:
  Tier 1 — same document content_hash → skip re-extract
  Tier 2 — same org + type + source external_id → merge
  Tier 3 — same org + type + dates within 30 days → candidate window
  Tier 4 — embedding cosine (deferred until embedding model exists)

Without embeddings, merges inside the tier-3 window are only applied for
*strong deterministic* matches (exact snippet, or exact normalized title).
That avoids false merges while still collapsing obvious duplicates.
"""

from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import evidence as evidence_repo
from app.repositories import signals as signals_repo
from app.repositories.documents import Document
from app.repositories.evidence import Evidence
from app.repositories.organizations import Organization
from app.repositories.scans import ScanRun
from app.repositories.signals import Signal

logger = logging.getLogger("app.services.signal_dedup")

_TIER3_DAYS = 30


@dataclass
class DedupRunResult:
    merged: int = 0
    evidence_appended: int = 0
    groups_collapsed: int = 0


async def document_already_extracted(
    session: AsyncSession, *, organization_id: uuid.UUID, content_hash: str
) -> bool:
    """Tier 1: this exact body was already extracted for the org."""
    value = await session.scalar(
        select(Evidence.evidence_id)
        .join(Signal, Signal.signal_id == Evidence.signal_id)
        .join(Document, Document.document_id == Evidence.document_id)
        .where(
            Signal.organization_id == organization_id,
            Signal.state == "validated",
            Document.content_hash == content_hash,
        )
        .limit(1)
    )
    return value is not None


async def find_survivor_for_candidate(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    signal_type: str,
    document: Document,
    title: str,
    snippet: str,
    published_on: date | None,
) -> Signal | None:
    """Return an existing validated signal this candidate should merge into, if any."""
    # Tier 2 — canonical source id (SAM noticeId, award id, …)
    if document.external_id:
        hit = await signals_repo.find_validated_by_external_id(
            session,
            organization_id=organization_id,
            signal_type=signal_type,
            external_id=document.external_id,
        )
        if hit is not None:
            return hit

    # Same document + type: second extraction from the same page
    hit = await signals_repo.find_validated_by_document_type(
        session,
        organization_id=organization_id,
        signal_type=signal_type,
        document_id=document.document_id,
        title_normalized=_normalize_title(title),
    )
    if hit is not None:
        return hit

    # Strong tier-3: exact snippet already on a validated signal of this type
    hit = await signals_repo.find_validated_by_snippet(
        session,
        organization_id=organization_id,
        signal_type=signal_type,
        snippet=snippet,
    )
    if hit is not None:
        return hit

    # Strong tier-3: exact normalized title within 30-day (or both undated) window
    hit = await signals_repo.find_validated_by_title_in_window(
        session,
        organization_id=organization_id,
        signal_type=signal_type,
        title_normalized=_normalize_title(title),
        published_on=published_on,
        window_days=_TIER3_DAYS,
    )
    return hit


async def merge_into_survivor(
    session: AsyncSession,
    *,
    survivor: Signal,
    document: Document,
    title: str,
    summary: str,
    snippet: str,
    relationship: str,
    published_on: date | None,
    data_origin: str,
) -> str:
    """Append evidence to survivor; record a merged shadow row. Never deletes evidence."""
    if await evidence_repo.has_identical_evidence(
        session,
        signal_id=survivor.signal_id,
        document_id=document.document_id,
        snippet=snippet,
    ):
        return "unchanged"

    await evidence_repo.create_evidence(
        session,
        signal_id=survivor.signal_id,
        document_id=document.document_id,
        source_id=document.source_id,
        source_url=document.source_url,
        published_on=published_on,
        snippet=snippet[:4000],
        relationship=relationship[:2000],
        data_origin=data_origin,
        retrieved_at=document.retrieved_at,
    )
    await signals_repo.create_signal(
        session,
        organization_id=survivor.organization_id,
        signal_type=survivor.signal_type,
        state="merged",
        title=title[:500],
        summary=summary[:4000],
        published_on=published_on,
        rejection_reason=None,
        ai_summary=relationship[:2000],
        data_origin=data_origin,
        merged_into_signal_id=survivor.signal_id,
    )
    return "merged"


async def dedupe_organization_signals(
    session: AsyncSession,
    *,
    scan: ScanRun,
    org: Organization,
) -> DedupRunResult:
    """Post-extract pass: collapse duplicate validated signals already stored for the org."""
    result = DedupRunResult()
    rows = await signals_repo.list_validated_for_organization(session, org.organization_id)
    if len(rows) < 2:
        scan.sources = list(scan.sources or []) + [
            {
                "source_name": "Signal dedup",
                "status": "succeeded",
                "detail": f"{len(rows)} validated; nothing to merge",
            }
        ]
        await session.flush()
        return result

    # Enrich with first evidence snippet + any external_id on linked docs
    enriched: list[tuple[Signal, str, str | None, str]] = []
    for signal in rows:
        evidence_rows = await evidence_repo.list_for_signal(session, signal.signal_id)
        snippet = evidence_rows[0].snippet if evidence_rows else ""
        external_id = None
        for ev in evidence_rows:
            doc = await session.get(Document, ev.document_id)
            if doc is not None and doc.external_id:
                external_id = doc.external_id
                break
        enriched.append((signal, snippet, external_id, _normalize_title(signal.title)))

    # Process oldest-first so the earliest signal survives
    enriched.sort(key=lambda item: (item[0].created_at, item[0].signal_id))

    claimed: set[uuid.UUID] = set()
    for i, (survivor, snip_a, ext_a, title_a) in enumerate(enriched):
        if survivor.signal_id in claimed or survivor.state != "validated":
            continue
        members = [survivor]
        for later, snip_b, ext_b, title_b in enriched[i + 1 :]:
            if later.signal_id in claimed or later.state != "validated":
                continue
            if later.signal_type != survivor.signal_type:
                continue
            if not _should_merge(
                survivor=survivor,
                other=later,
                snippet_a=snip_a,
                snippet_b=snip_b,
                title_a=title_a,
                title_b=title_b,
                external_a=ext_a,
                external_b=ext_b,
            ):
                continue
            members.append(later)

        if len(members) == 1:
            continue

        result.groups_collapsed += 1
        for duplicate in members[1:]:
            moved = await _collapse_validated_into(session, survivor=survivor, duplicate=duplicate)
            result.merged += 1
            result.evidence_appended += moved
            claimed.add(duplicate.signal_id)
            duplicate.state = "merged"
            duplicate.merged_into_signal_id = survivor.signal_id
            duplicate.rejection_reason = None

    scan.signals_updated = int(scan.signals_updated or 0) + result.merged
    scan.stage = "deduplicating"
    scan.sources = list(scan.sources or []) + [
        {
            "source_name": "Signal dedup",
            "status": "succeeded",
            "detail": (
                f"{result.groups_collapsed} groups, {result.merged} merged, "
                f"{result.evidence_appended} evidence moved"
            ),
        }
    ]
    await session.flush()
    return result


def _should_merge(
    *,
    survivor: Signal,
    other: Signal,
    snippet_a: str,
    snippet_b: str,
    title_a: str,
    title_b: str,
    external_a: str | None,
    external_b: str | None,
) -> bool:
    if external_a and external_b and external_a == external_b:
        return True
    if snippet_a and snippet_b and snippet_a == snippet_b:
        return True
    if title_a and title_b and title_a == title_b and _dates_within_window(
        survivor.published_on, other.published_on, _TIER3_DAYS
    ):
        return True
    return False


def _dates_within_window(a: date | None, b: date | None, days: int) -> bool:
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return abs((a - b).days) <= days


async def _collapse_validated_into(
    session: AsyncSession, *, survivor: Signal, duplicate: Signal
) -> int:
    """Move evidence from duplicate onto survivor. Duplicate row stays as merged."""
    moved = 0
    for ev in await evidence_repo.list_for_signal(session, duplicate.signal_id):
        if await evidence_repo.has_identical_evidence(
            session,
            signal_id=survivor.signal_id,
            document_id=ev.document_id,
            snippet=ev.snippet,
        ):
            continue
        ev.signal_id = survivor.signal_id
        moved += 1
    await session.flush()
    return moved


def _normalize_title(value: str) -> str:
    text = value.lower().strip()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text
