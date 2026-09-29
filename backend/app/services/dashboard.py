"""Dashboard read model (API_CONTRACT §10). Reads only; never writes or calls a model.

Every figure comes from stored validated signals, opportunities, scores, and scan rows.
`ai_insights` reuses the already-stored, grounded score explanations. Nothing is generated here.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import dashboard as dashboard_repo
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
# The scan chip only reads the latest batch cohort (one run per tracked organization, 10–20 in
# the MVP) plus any run still active, so three batches' worth of rows is enough.
_SCAN_RUNS_FOR_STATUS = 60
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
    by_type = dict.fromkeys(SIGNAL_TYPES, 0)
    recent_by_type: dict[str, int] = {}
    per_day: dict = {}
    for signal_type, day, count in await dashboard_repo.validated_counts_by_type_and_day(session):
        by_type[signal_type] = by_type.get(signal_type, 0) + count
        if day is not None and day >= window_start:
            recent_by_type[signal_type] = recent_by_type.get(signal_type, 0) + count
            if day <= today:
                per_day[day] = per_day.get(day, 0) + count
    by_type = {signal_type: by_type[signal_type] for signal_type in SIGNAL_TYPES}
    recent_count = sum(recent_by_type.values())
    competitor_new = recent_by_type.get("competitor_vendor", 0)

    volume = [
        SignalVolumePoint(date=day, count=per_day.get(day, 0))
        for day in (window_start + timedelta(days=i) for i in range(_WINDOW_DAYS))
    ]

    recent_rows = await dashboard_repo.recent_validated_signals(
        session, limit=_MAX_RECENT_SIGNALS
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
            source_count=evidence_count,
            data_origin=signal.data_origin,
        )
        for signal, organization_name, evidence_count in recent_rows
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
        scan_status=_scan_status(
            await dashboard_repo.recent_scan_runs(session, limit=_SCAN_RUNS_FOR_STATUS)
        ),
        prioritized_opportunities=prioritized,
        recent_signals=recent_signals,
        signal_volume=volume,
        ai_insights=insights,
    )


def _scan_status(runs: list[ScanRun]) -> DashboardScanStatus:
    """Portfolio scan chip for the Command Center (API_CONTRACT §10).

    Prefer batch health over a single org. Org runs marked ``partial`` (for example one
    page URL failed while others collected) count as healthy for this chip — show
    ``current``, not failed. Interrupted runs are ``partial``. Red ``failed`` only when
    the latest finished cohort has no successful or soft-success org runs.
    """
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
    if last.batch_id is not None:
        cohort = [
            run
            for run in runs
            if run.batch_id == last.batch_id and run.status in _TERMINAL_STATUSES
        ]
        if not cohort:
            cohort = [last]
    else:
        cohort = [last]

    # Soft success: org finished useful work even if a page/source row failed.
    healthy = sum(1 for run in cohort if run.status in ("succeeded", "partial"))
    failed = sum(1 for run in cohort if run.status == "failed")
    interrupted = sum(1 for run in cohort if run.status == "interrupted")

    sources_failed = sum(
        1
        for run in cohort
        for source in (run.sources or [])
        if isinstance(source, dict) and source.get("status") == "failed"
    )

    if running:
        state = "running"
    elif healthy and not failed and not interrupted:
        state = "current"
    elif healthy and (failed or interrupted):
        state = "partial"
    elif interrupted and not failed and not healthy:
        state = "partial"
    elif failed and not healthy:
        state = "failed"
    elif last.status in ("succeeded", "partial"):
        state = "current"
    elif last.status == "interrupted":
        state = "partial"
    else:
        state = "failed"

    return DashboardScanStatus(
        state=state,
        last_finished_at=last.finished_at,
        running=running,
        last_status=last.status,
        sources_failed=sources_failed,
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
