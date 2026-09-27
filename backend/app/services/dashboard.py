"""Dashboard read model (API_CONTRACT §10). Reads only; never writes or calls a model.

Every figure comes from stored validated signals, opportunities, scores, and scan rows.
`ai_insights` reuses the already-stored, grounded score explanations. Nothing is generated here.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import dashboard as dashboard_repo
from app.repositories import evidence as evidence_repo
from app.repositories.scans import ScanRun
from app.repositories.signals import SIGNAL_TYPES
from app.schemas.dashboard import (
    DashboardCompetitorVendor,
    DashboardInsight,
    DashboardOpportunities,
    DashboardResponse,
    DashboardScanStatus,
    DashboardSignals,
    SignalVolumePoint,
)
from app.schemas.opportunities import OpportunitySummary
from app.schemas.signals import EvidenceItem, SignalSummary

_BANDS = ("high", "medium", "low", "monitor")
_WINDOW_DAYS = 30
_NEW_OPPORTUNITY_DAYS = 7
_MAX_PRIORITIZED = 5
_MAX_RECENT_SIGNALS = 6
_MAX_INSIGHTS = 3
_EVIDENCE_PER_INSIGHT = 3
_ACTIVE_STATUSES = ("queued", "running")
_TERMINAL_STATUSES = ("succeeded", "partial", "failed", "interrupted")


async def build_dashboard(session: AsyncSession) -> DashboardResponse:
    # Reuse the exact summary mapper behind /opportunities so both views always agree.
    from app.api.v1.opportunities import _summary as opportunity_summary

    now = datetime.now(timezone.utc)
    today = now.date()
    window_start = today - timedelta(days=_WINDOW_DAYS - 1)
    new_since = now - timedelta(days=_NEW_OPPORTUNITY_DAYS)

    # --- opportunities -------------------------------------------------------------
    rows = await dashboard_repo.opportunity_rows(session)
    rows.sort(key=lambda row: row[2].value if row[2] is not None else -1, reverse=True)

    by_band = dict.fromkeys(_BANDS, 0)
    for _opportunity, _organization, score, _count in rows:
        band = score.band if score is not None and score.band in by_band else "monitor"
        by_band[band] += 1
    new_count = sum(1 for opportunity, *_rest in rows if opportunity.created_at >= new_since)

    top_rows = rows[:_MAX_PRIORITIZED]
    prioritized: list[OpportunitySummary] = [
        opportunity_summary(opportunity, organization, score, signal_count)
        for opportunity, organization, score, signal_count in top_rows
    ]

    # --- signals -------------------------------------------------------------------
    counts = await dashboard_repo.validated_counts(session, since=window_start)
    by_type = {signal_type: counts.get(signal_type, (0, 0))[0] for signal_type in SIGNAL_TYPES}
    recent_count = sum(recent for _total, recent in counts.values())
    competitor_new = counts.get("competitor_vendor", (0, 0))[1]

    per_day = await dashboard_repo.validated_counts_per_day(
        session, since=window_start, until=today
    )
    volume = [
        SignalVolumePoint(date=day, count=per_day.get(day, 0))
        for day in (window_start + timedelta(days=i) for i in range(_WINDOW_DAYS))
    ]

    recent_rows = await dashboard_repo.recent_validated_signals(
        session, limit=_MAX_RECENT_SIGNALS
    )
    evidence_counts = await evidence_repo.count_for_signals(
        session, [signal.signal_id for signal, _name in recent_rows]
    )
    recent_signals = [
        SignalSummary(
            signal_id=signal.signal_id,
            organization_id=signal.organization_id,
            organization_name=organization_name,
            signal_type=signal.signal_type,
            state=signal.state,
            title=signal.title,
            summary=signal.summary,
            date=signal.published_on,
            date_status="available" if signal.published_on else "unavailable",
            source_count=evidence_counts.get(signal.signal_id, 0),
            data_origin=signal.data_origin,
        )
        for signal, organization_name in recent_rows
    ]

    # --- grounded insights (stored explanations only) -------------------------------
    insights = await _insights(session, top_rows)

    cached = (
        any(item.data_origin == "cached" for item in prioritized)
        or any(item.data_origin == "cached" for item in recent_signals)
        or any(ev.data_origin == "cached" for ins in insights for ev in ins.evidence)
    )

    return DashboardResponse(
        generated_at=now,
        data_origin="cached" if cached else "live",
        opportunities=DashboardOpportunities(
            total=len(rows), by_band=by_band, new_since=new_since, new_count=new_count
        ),
        signals=DashboardSignals(
            validated_total=sum(by_type.values()),
            by_type=by_type,
            recent_window_days=_WINDOW_DAYS,
            recent_count=recent_count,
        ),
        competitor_vendor=DashboardCompetitorVendor(
            validated_total=by_type.get("competitor_vendor", 0), new_in_window=competitor_new
        ),
        scan_status=_scan_status(await dashboard_repo.recent_scan_runs(session)),
        prioritized_opportunities=prioritized,
        recent_signals=recent_signals,
        signal_volume=volume,
        ai_insights=insights,
    )


def _scan_status(runs: list[ScanRun]) -> DashboardScanStatus:
    running = any(run.status in _ACTIVE_STATUSES for run in runs)
    finished = [
        run for run in runs if run.status in _TERMINAL_STATUSES and run.finished_at is not None
    ]
    if not finished:
        return DashboardScanStatus(
            state="running" if running else "never_scanned",
            last_finished_at=None,
            running=running,
            last_status=None,
            sources_failed=0,
        )

    last = max(finished, key=lambda run: run.finished_at)
    batch = [run for run in runs if last.batch_id is not None and run.batch_id == last.batch_id]
    failed = sum(
        1
        for run in (batch or [last])
        for source in (run.sources or [])
        if isinstance(source, dict) and source.get("status") == "failed"
    )
    if running:
        state = "running"
    elif last.status == "succeeded":
        state = "current"
    elif last.status == "partial":
        state = "partial"
    else:
        state = "failed"
    return DashboardScanStatus(
        state=state,
        last_finished_at=last.finished_at,
        running=running,
        last_status=last.status,
        sources_failed=failed,
    )


async def _insights(session: AsyncSession, top_rows: list) -> list[DashboardInsight]:
    candidates = [
        (opportunity, organization, score)
        for opportunity, organization, score, _count in top_rows
        if score is not None and score.explanation_status == "ready" and score.explanation_text
    ][:_MAX_INSIGHTS * 2]
    if not candidates:
        return []

    grouped: dict = {}
    for opportunity_id, ev, source_name in await dashboard_repo.evidence_for_opportunities(
        session, [opportunity.opportunity_id for opportunity, _org, _score in candidates]
    ):
        grouped.setdefault(opportunity_id, []).append((ev, source_name))

    insights: list[DashboardInsight] = []
    for opportunity, organization, score in candidates:
        if len(insights) >= _MAX_INSIGHTS:
            break
        items = [
            EvidenceItem(
                evidence_id=ev.evidence_id,
                source_name=source_name or f"{organization.name} official website",
                source_url=ev.source_url,
                date=ev.published_on,
                date_status="available" if ev.published_on else "unavailable",
                snippet=ev.snippet,
                relationship=ev.relationship,
                data_origin=ev.data_origin,
                retrieved_at=ev.retrieved_at,
            )
            for ev, source_name in grouped.get(opportunity.opportunity_id, [])[
                :_EVIDENCE_PER_INSIGHT
            ]
        ]
        if not items:
            continue  # An insight without evidence is not shown (API_CONTRACT §10).
        insights.append(
            DashboardInsight(
                text=f"{organization.name}: {score.explanation_text}",
                evidence_ids=[item.evidence_id for item in items],
                evidence=items,
            )
        )
    return insights
