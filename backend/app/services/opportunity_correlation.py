"""Correlate validated signals → one potential opportunity + rules score (M7).

AI_RAG_DESIGN.md §§8–10. Score explanation (M8) left unavailable.
"""

from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.adapters.base import LLMProviderAdapter
from app.repositories import evidence as evidence_repo
from app.repositories import opportunities as opportunities_repo
from app.repositories import opportunity_scores as scores_repo
from app.repositories import signals as signals_repo
from app.repositories.evidence import Evidence
from app.repositories.organizations import Organization
from app.repositories.scans import ScanRun
from app.repositories.signals import Signal
from app.repositories.sources import Source
from app.scoring.v1 import ScoreInputSignal, score_opportunity

logger = logging.getLogger("app.services.opportunity_correlation")

_TIME_WINDOW_DAYS = 180
_RECENCY_GATE_DAYS = 90
_MIN_SCORE = 50

_COMPLEMENTARY = frozenset(
    {
        "technology_initiative",
        "leadership_change",
        "strategic_announcement",
        "competitor_vendor",
        "funding_budget",
    }
)
_PROCUREMENTISH = frozenset({"procurement", "contract_renewal"})

_STOP = frozenset(
    {
        "about",
        "after",
        "among",
        "being",
        "between",
        "their",
        "there",
        "these",
        "those",
        "which",
        "where",
        "while",
        "would",
        "could",
        "should",
        "university",
        "college",
        "school",
        "district",
        "student",
        "students",
        "campus",
        "official",
        "public",
        "https",
        "http",
        "www",
    }
)


@dataclass
class _SignalView:
    signal: Signal
    evidence: list[Evidence]
    snippet_text: str
    reliability_label: str | None
    newest_retrieved: datetime | None


@dataclass
class CorrelationRunResult:
    created: int = 0
    updated: int = 0
    scored: int = 0
    skipped_reason: str | None = None
    score_value: int | None = None
    opportunity_id: uuid.UUID | None = None
    previous_score: int | None = None


async def correlate_organization_opportunity(
    session: AsyncSession,
    *,
    llm: LLMProviderAdapter,
    scan: ScanRun,
    org: Organization,
) -> CorrelationRunResult:
    """Run after dedup. No opportunity when the generation rule fails (first create)."""
    result = CorrelationRunResult()
    scan.stage = "correlating"
    await session.commit()

    validated = await signals_repo.list_validated_for_organization(
        session, org.organization_id
    )
    if len(validated) < 2:
        result.skipped_reason = "fewer_than_two_validated_signals"
        await _record_source(session, scan, "succeeded", result.skipped_reason)
        return result

    views = await _load_views(session, validated)
    today = datetime.now(timezone.utc).date()
    groups = _connected_groups(views, scan_date=today)
    qualifying = [g for g in groups if _group_has_two_types(g)]
    if not qualifying:
        result.skipped_reason = "no_correlated_group"
        await _record_source(session, scan, "succeeded", result.skipped_reason)
        return result

    # Prefer the group with the highest rules score, then most distinct types.
    ranked: list[tuple[int, int, list[_SignalView]]] = []
    for group in qualifying:
        breakdown = score_opportunity(_to_score_inputs(group), now=today)
        ranked.append((breakdown.value, len({v.signal.signal_type for v in group}), group))
    ranked.sort(key=lambda item: (item[0], item[1], len(item[2])), reverse=True)
    _, _, best_group = ranked[0]
    breakdown = score_opportunity(_to_score_inputs(best_group), now=today)
    existing = await opportunities_repo.get_by_organization(session, org.organization_id)

    # First create only when the generation rule passes. Later scans may rescore below 50 (§25).
    if existing is None:
        if not _meets_recency_gate(best_group, today=today):
            result.skipped_reason = "recency_gate_failed"
            await _record_source(session, scan, "succeeded", result.skipped_reason)
            return result
        if breakdown.value < _MIN_SCORE:
            result.skipped_reason = f"score_below_{_MIN_SCORE}"
            result.score_value = breakdown.value
            await _record_source(session, scan, "succeeded", result.skipped_reason)
            return result

    correlation_text = await _correlation_text(llm, org=org, group=best_group)
    data_origin = (
        "cached"
        if any(v.signal.data_origin == "cached" for v in best_group)
        or any(ev.data_origin == "cached" for v in best_group for ev in v.evidence)
        else "live"
    )

    previous = None
    if existing is not None:
        prev_score = await scores_repo.latest_for_opportunity(session, existing.opportunity_id)
        previous = prev_score.value if prev_score is not None else None

    scan.stage = "scoring"
    await session.commit()

    opportunity = await opportunities_repo.upsert_opportunity(
        session,
        organization_id=org.organization_id,
        correlation_text=correlation_text,
        data_origin=data_origin,
        recommended_action_text=None,
    )
    signal_ids = [v.signal.signal_id for v in best_group]
    await opportunities_repo.replace_opportunity_signals(
        session, opportunity_id=opportunity.opportunity_id, signal_ids=signal_ids
    )
    score_row = await scores_repo.insert_score(
        session,
        opportunity_id=opportunity.opportunity_id,
        breakdown=breakdown,
        explanation_text=None,
        explanation_status="unavailable",
    )

    # M8: explain the stored number. Failure leaves explanation unavailable (score stays).
    explanation = await _score_explanation(
        llm,
        org=org,
        breakdown=breakdown,
        group=best_group,
    )
    if explanation:
        await scores_repo.set_explanation(
            session, score_id=score_row.score_id, explanation_text=explanation
        )

    if existing is None:
        result.created = 1
        scan.opportunities_created = int(scan.opportunities_created or 0) + 1
    else:
        result.updated = 1
        scan.opportunities_updated = int(scan.opportunities_updated or 0) + 1

    result.scored = 1
    result.score_value = breakdown.value
    result.opportunity_id = opportunity.opportunity_id
    result.previous_score = previous

    explain_note = "explanation=ready" if explanation else "explanation=unavailable"
    detail = (
        f"opportunity={opportunity.opportunity_id} score={breakdown.value} "
        f"band={breakdown.band} signals={len(signal_ids)} types="
        f"{sorted({v.signal.signal_type for v in best_group})} {explain_note}"
    )
    await _record_source(session, scan, "succeeded", detail)
    return result


async def _score_explanation(
    llm: LLMProviderAdapter,
    *,
    org: Organization,
    breakdown,
    group: list[_SignalView],
) -> str | None:
    snippets = [v.snippet_text[:350] for v in group if v.snippet_text]
    types = sorted({v.signal.signal_type for v in group})
    try:
        text = await llm.explain_score(
            organization_name=org.name,
            score_value=breakdown.value,
            score_band=breakdown.band,
            weight_version=breakdown.weight_version,
            factors={
                "procurement_relevance": breakdown.procurement_relevance,
                "related_signal_strength": breakdown.related_signal_strength,
                "assessment_edtech_relevance": breakdown.assessment_edtech_relevance,
                "recency": breakdown.recency,
                "source_reliability": breakdown.source_reliability,
            },
            signal_types=types,
            snippets=snippets,
        )
    except Exception:
        logger.exception("Score explanation LLM failed; leaving unavailable")
        return None
    cleaned = (text or "").strip()
    if not cleaned:
        return None
    if not _explanation_text_ok(cleaned, value=breakdown.value, band=breakdown.band):
        logger.warning(
            "Score explanation rejected (must repeat value/band; no predictive language)"
        )
        return None
    return cleaned[:2500]


def _explanation_text_ok(text: str, *, value: int, band: str) -> bool:
    lower = text.lower()
    if str(value) not in text:
        return False
    if band.lower() not in lower:
        return False
    return not any(phrase in lower for phrase in _FORBIDDEN)

async def _load_views(session: AsyncSession, signals: list[Signal]) -> list[_SignalView]:
    views: list[_SignalView] = []
    source_cache: dict[uuid.UUID, Source | None] = {}
    for signal in signals:
        evidence = await evidence_repo.list_for_signal(session, signal.signal_id)
        snippets = " ".join(ev.snippet for ev in evidence if ev.snippet)
        reliability: str | None = None
        newest: datetime | None = None
        for ev in evidence:
            if newest is None or (ev.retrieved_at and ev.retrieved_at > newest):
                newest = ev.retrieved_at
            label = await _reliability_for_evidence(session, ev, source_cache)
            if label == "official_api":
                reliability = label
            elif label == "official_website" and reliability != "official_api":
                reliability = label
            elif label and reliability is None:
                reliability = label
        views.append(
            _SignalView(
                signal=signal,
                evidence=evidence,
                snippet_text=snippets or signal.summary,
                reliability_label=reliability,
                newest_retrieved=newest,
            )
        )
    return views


async def _reliability_for_evidence(
    session: AsyncSession,
    evidence: Evidence,
    cache: dict[uuid.UUID, Source | None],
) -> str | None:
    if evidence.source_id is None:
        return "official_website"
    if evidence.source_id not in cache:
        cache[evidence.source_id] = await session.get(Source, evidence.source_id)
    source = cache[evidence.source_id]
    if source is None:
        return "other_public"
    return source.reliability_label or "other_public"


def _connected_groups(views: list[_SignalView], *, scan_date: date) -> list[list[_SignalView]]:
    n = len(views)
    parent = list(range(n))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i: int, j: int) -> None:
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[rj] = ri

    for i in range(n):
        for j in range(i + 1, n):
            if _can_correlate(views[i], views[j], scan_date=scan_date):
                union(i, j)

    buckets: dict[int, list[_SignalView]] = {}
    for i in range(n):
        buckets.setdefault(find(i), []).append(views[i])
    return list(buckets.values())


def _can_correlate(a: _SignalView, b: _SignalView, *, scan_date: date) -> bool:
    if a.signal.signal_id == b.signal.signal_id:
        return False
    if a.signal.signal_type == b.signal.signal_type:
        # Same type only joins a multi-type group via a different-type bridge (union-find).
        # Pairwise same-type alone does not start a group for opportunities.
        return False
    if not _time_ok(a, b, scan_date=scan_date):
        return False
    return _subject_overlap(a, b)


def _time_ok(a: _SignalView, b: _SignalView, *, scan_date: date) -> bool:
    da, db = a.signal.published_on, b.signal.published_on
    if da is None and db is None:
        # Waived; subject overlap must carry (checked separately).
        return True
    if da is not None and db is not None:
        return abs((da - db).days) <= _TIME_WINDOW_DAYS
    dated = da if da is not None else db
    assert dated is not None
    return abs((dated - scan_date).days) <= _TIME_WINDOW_DAYS


def _subject_overlap(a: _SignalView, b: _SignalView) -> bool:
    ta, tb = a.signal.signal_type, b.signal.signal_type
    if (ta in _PROCUREMENTISH and tb in _COMPLEMENTARY) or (
        tb in _PROCUREMENTISH and ta in _COMPLEMENTARY
    ):
        return True
    tokens_a = _content_tokens(a.snippet_text + " " + a.signal.title)
    tokens_b = _content_tokens(b.snippet_text + " " + b.signal.title)
    return bool(tokens_a & tokens_b)


def _content_tokens(text: str) -> set[str]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9\-]{3,}", text.lower())
    return {w for w in words if w not in _STOP}


def _group_has_two_types(group: list[_SignalView]) -> bool:
    return len({v.signal.signal_type for v in group}) >= 2 and len(group) >= 2


def _meets_recency_gate(group: list[_SignalView], *, today: date) -> bool:
    for v in group:
        if v.signal.published_on is not None:
            if (today - v.signal.published_on).days <= _RECENCY_GATE_DAYS:
                return True
        elif v.newest_retrieved is not None:
            retrieved = v.newest_retrieved.astimezone(timezone.utc).date()
            if (today - retrieved).days <= _RECENCY_GATE_DAYS:
                return True
    return False


def _to_score_inputs(group: list[_SignalView]) -> list[ScoreInputSignal]:
    return [
        ScoreInputSignal(
            signal_type=v.signal.signal_type,
            published_on=v.signal.published_on,
            snippet=v.snippet_text,
            reliability_label=v.reliability_label,
        )
        for v in group
    ]


async def _correlation_text(
    llm: LLMProviderAdapter, *, org: Organization, group: list[_SignalView]
) -> str:
    payload = [
        {
            "signal_type": v.signal.signal_type,
            "title": v.signal.title,
            "snippet": (v.evidence[0].snippet if v.evidence else v.signal.summary)[:400],
        }
        for v in group
    ]
    try:
        text = await llm.correlate_signals(
            organization_name=org.name,
            signals=payload,
        )
        cleaned = (text or "").strip()
        if cleaned and _correlation_text_ok(cleaned):
            return cleaned[:2000]
    except Exception:
        logger.exception("Correlation LLM failed; using fallback text")
    types = ", ".join(sorted({v.signal.signal_type for v in group}))
    return (
        f"Validated signals for {org.name} of types [{types}] were grouped because they "
        f"share this organization and fall within the correlation window. Review the stored "
        f"snippets for subject overlap. This is a potential opportunity, not a confirmed deal."
    )


_FORBIDDEN = (
    "will issue an rfp",
    "will issue a rfp",
    "expected procurement",
    "confirmed opportunity",
    "rfp will happen",
    "guaranteed",
)


def _correlation_text_ok(text: str) -> bool:
    lower = text.lower()
    return not any(phrase in lower for phrase in _FORBIDDEN)


async def _record_source(
    session: AsyncSession, scan: ScanRun, status: str, detail: str | None
) -> None:
    scan.sources = list(scan.sources or []) + [
        {
            "source_name": "Opportunity correlation",
            "status": status,
            "detail": detail,
        }
    ]
    await session.flush()
