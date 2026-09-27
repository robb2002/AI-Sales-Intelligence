"""Competitor digest (API_CONTRACT §10a, AI_RAG_DESIGN §26).

Stored, validated signals of COMPETITOR organizations and their evidence. No model is called and
nothing is inferred here: a competitor with no validated signal says so.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import competitors as competitors_repo
from app.schemas.competitors import (
    CompetitorEntry,
    CompetitorSignal,
    CompetitorsResponse,
    CompetitorTotals,
)
from app.schemas.signals import EvidenceItem

_WINDOW_DAYS = 30
_SIGNALS_PER_COMPETITOR = 5
_EVIDENCE_PER_SIGNAL = 2


async def build_competitors(session: AsyncSession) -> CompetitorsResponse:
    now = datetime.now(timezone.utc)
    window_start = now.date() - timedelta(days=_WINDOW_DAYS - 1)

    organizations = await competitors_repo.competitor_organizations(session)
    org_ids = [org.organization_id for org in organizations]
    last_scans = await competitors_repo.last_finished_scans(session, org_ids)
    all_signals = await competitors_repo.validated_signals(session, org_ids)

    by_org: dict = {}
    for signal in all_signals:
        by_org.setdefault(signal.organization_id, []).append(signal)

    shown = [s for signals in by_org.values() for s in signals[:_SIGNALS_PER_COMPETITOR]]
    evidence_by_signal: dict = {}
    for evidence, source_name in await competitors_repo.evidence_for_signals(
        session, [signal.signal_id for signal in shown]
    ):
        bucket = evidence_by_signal.setdefault(evidence.signal_id, [])
        if len(bucket) < _EVIDENCE_PER_SIGNAL:
            bucket.append((evidence, source_name))

    cached = False
    entries: list[CompetitorEntry] = []
    for org in organizations:
        signals = by_org.get(org.organization_id, [])
        items: list[CompetitorSignal] = []
        for signal in signals[:_SIGNALS_PER_COMPETITOR]:
            cached = cached or signal.data_origin == "cached"
            evidence_items = [
                EvidenceItem(
                    evidence_id=ev.evidence_id,
                    source_name=source_name or f"{org.name} official website",
                    source_url=ev.source_url,
                    date=ev.published_on,
                    date_status="available" if ev.published_on else "unavailable",
                    snippet=ev.snippet,
                    relationship=ev.relationship,
                    data_origin=ev.data_origin,
                    retrieved_at=ev.retrieved_at,
                )
                for ev, source_name in evidence_by_signal.get(signal.signal_id, [])
            ]
            items.append(
                CompetitorSignal(
                    signal_id=signal.signal_id,
                    organization_id=signal.organization_id,
                    organization_name=org.name,
                    signal_type=signal.signal_type,
                    state=signal.state,
                    title=signal.title,
                    summary=signal.summary,
                    date=signal.published_on,
                    date_status="available" if signal.published_on else "unavailable",
                    source_count=len(evidence_items),
                    data_origin=signal.data_origin,
                    evidence=evidence_items,
                )
            )
        entries.append(
            CompetitorEntry(
                organization_id=org.organization_id,
                name=org.name,
                website_url=org.website_url,
                tracking_status=org.tracking_status,
                last_scanned_at=last_scans.get(org.organization_id),
                validated_signal_count=len(signals),
                signals=items,
            )
        )

    new_in_window = sum(
        1
        for signal in all_signals
        if (signal.published_on or signal.created_at.date()) >= window_start
    )
    return CompetitorsResponse(
        generated_at=now,
        data_origin="cached" if cached else "live",
        totals=CompetitorTotals(
            competitors=len(organizations),
            validated_signals=len(all_signals),
            new_in_window=new_in_window,
            window_days=_WINDOW_DAYS,
        ),
        competitors=entries,
    )
