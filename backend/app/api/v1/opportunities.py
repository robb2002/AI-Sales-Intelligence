from __future__ import annotations

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, require_app_user
from app.core.errors import NotFoundError, ValidationAppError
from app.core.security import CurrentUser
from app.repositories import evidence as evidence_repo
from app.repositories import opportunities as opportunities_repo
from app.repositories import opportunity_scores as scores_repo
from app.repositories.opportunity_scores import OpportunityScore
from app.repositories.organizations import ORGANIZATION_TYPES, Organization
from app.repositories.signals import Signal
from app.repositories.sources import Source
from app.schemas.opportunities import (
    CorrelationPayload,
    OpportunityDetail,
    OpportunityPage,
    OpportunitySummary,
    RecommendedActionPayload,
    ScoreExplanation,
    ScoreFactor,
    ScorePayload,
)
from app.schemas.signals import EvidenceItem, SignalSummary

router = APIRouter(tags=["opportunities"])

_BANDS = frozenset({"high", "medium", "low", "monitor"})
_FACTOR_MAX = {
    "procurement_relevance": 30,
    "related_signal_strength": 25,
    "assessment_edtech_relevance": 20,
    "recency": 15,
    "source_reliability": 10,
}


@router.get("/opportunities", response_model=OpportunityPage)
async def list_opportunities(
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[CurrentUser, Depends(require_app_user)],
    organization_id: Annotated[UUID | None, Query()] = None,
    organization_type: Annotated[list[str] | None, Query()] = None,
    state_code: Annotated[list[str] | None, Query()] = None,
    band: Annotated[list[str] | None, Query()] = None,
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
    sort: Annotated[str, Query()] = "score",
    direction: Annotated[str, Query()] = "desc",
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> OpportunityPage:
    if organization_type:
        bad = [t for t in organization_type if t not in ORGANIZATION_TYPES]
        if bad:
            raise ValidationAppError(message=f"Invalid organization_type: {bad[0]}")
    if band:
        bad_b = [b for b in band if b not in _BANDS]
        if bad_b:
            raise ValidationAppError(message=f"Invalid band: {bad_b[0]}")
    if sort not in ("score", "updated_at"):
        raise ValidationAppError(message="sort must be score or updated_at")
    if direction not in ("asc", "desc"):
        raise ValidationAppError(message="direction must be asc or desc")
    if date_from and date_to and date_from > date_to:
        raise ValidationAppError(message="date_from must be on or before date_to")

    rows, total = await opportunities_repo.list_opportunities(
        session,
        organization_id=organization_id,
        organization_types=organization_type,
        state_codes=state_code,
        bands=band,
        date_from=date_from,
        date_to=date_to,
        sort=sort,
        direction=direction,
        limit=limit,
        offset=offset,
    )
    data = [
        _summary(opportunity, organization, score, signal_count)
        for opportunity, organization, score, signal_count in rows
    ]
    return OpportunityPage(data=data, total=total, limit=limit, offset=offset)


@router.get("/opportunities/{opportunity_id}", response_model=OpportunityDetail)
async def get_opportunity(
    opportunity_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[CurrentUser, Depends(require_app_user)],
) -> OpportunityDetail:
    opportunity = await opportunities_repo.get_by_id(session, opportunity_id)
    if opportunity is None:
        raise NotFoundError("opportunity")
    organization = await session.get(Organization, opportunity.organization_id)
    if organization is None:
        raise NotFoundError("organization")

    score = await scores_repo.latest_for_opportunity(session, opportunity_id)
    previous = await _previous_score_value(session, opportunity_id, score)
    signal_ids = await opportunities_repo.list_signal_ids(session, opportunity_id)
    signal_rows: list[Signal] = []
    for sid in signal_ids:
        row = await session.get(Signal, sid)
        if row is not None:
            signal_rows.append(row)
    evidence_counts = await evidence_repo.count_for_signals(session, signal_ids)
    signal_summaries = [
        SignalSummary(
            signal_id=row.signal_id,
            organization_id=row.organization_id,
            organization_name=organization.name,
            signal_type=row.signal_type,
            state=row.state,
            title=row.title,
            summary=row.summary,
            date=row.published_on,
            date_status="available" if row.published_on else "unavailable",
            source_count=evidence_counts.get(row.signal_id, 0),
            data_origin=row.data_origin,
        )
        for row in signal_rows
    ]

    evidence_items: list[EvidenceItem] = []
    evidence_ids: list[UUID] = []
    for sid in signal_ids:
        for ev in await evidence_repo.list_for_signal(session, sid):
            source_name = organization.name
            if ev.source_id is not None:
                source = await session.get(Source, ev.source_id)
                if source is not None:
                    source_name = source.name
            else:
                source_name = f"{organization.name} official website"
            evidence_items.append(
                EvidenceItem(
                    evidence_id=ev.evidence_id,
                    source_name=source_name,
                    source_url=ev.source_url,
                    date=ev.published_on,
                    date_status="available" if ev.published_on else "unavailable",
                    snippet=ev.snippet,
                    relationship=ev.relationship,
                    data_origin=ev.data_origin,
                    retrieved_at=ev.retrieved_at,
                )
            )
            evidence_ids.append(ev.evidence_id)

    summary = _summary(
        opportunity, organization, score, len(signal_ids), previous_value=previous
    )
    recommended = None
    if opportunity.recommended_action_text:
        recommended = RecommendedActionPayload(
            text=opportunity.recommended_action_text,
            evidence_ids=evidence_ids,
        )
    return OpportunityDetail(
        **summary.model_dump(),
        label=opportunity.label,
        signals=signal_summaries,
        correlation=CorrelationPayload(
            text=opportunity.correlation_text,
            evidence_ids=evidence_ids,
        ),
        recommended_action=recommended,
        evidence=evidence_items,
    )


def _summary(
    opportunity,
    organization: Organization,
    score: OpportunityScore | None,
    signal_count: int,
    previous_value: int | None = None,
) -> OpportunitySummary:
    return OpportunitySummary(
        opportunity_id=opportunity.opportunity_id,
        organization_id=opportunity.organization_id,
        organization_name=organization.name,
        organization_type=organization.organization_type,
        state_code=organization.state_code,
        score=_score_payload(score, previous_value=previous_value),
        signal_count=signal_count,
        updated_at=opportunity.updated_at,
        data_origin=opportunity.data_origin,
    )


def _score_payload(
    score: OpportunityScore | None, *, previous_value: int | None = None
) -> ScorePayload:
    if score is None:
        return ScorePayload(
            value=0,
            band="monitor",
            weight_version="v1",
            factors=[
                ScoreFactor(key=k, points=0, max_points=m) for k, m in _FACTOR_MAX.items()
            ],
            explanation=None,
            explanation_status="unavailable",
            previous_value=None,
            scored_at=None,
        )
    explanation = None
    if score.explanation_status == "ready" and score.explanation_text:
        explanation = ScoreExplanation(text=score.explanation_text)
    return ScorePayload(
        value=score.value,
        band=score.band,
        weight_version=score.weight_version,
        factors=[
            ScoreFactor(
                key="procurement_relevance",
                points=score.procurement_relevance,
                max_points=30,
            ),
            ScoreFactor(
                key="related_signal_strength",
                points=score.related_signal_strength,
                max_points=25,
            ),
            ScoreFactor(
                key="assessment_edtech_relevance",
                points=score.assessment_edtech_relevance,
                max_points=20,
            ),
            ScoreFactor(key="recency", points=score.recency, max_points=15),
            ScoreFactor(
                key="source_reliability",
                points=score.source_reliability,
                max_points=10,
            ),
        ],
        explanation=explanation,
        explanation_status=score.explanation_status,
        previous_value=previous_value,
        scored_at=score.scored_at,
    )


async def _previous_score_value(
    session: AsyncSession, opportunity_id: UUID, current: OpportunityScore | None
) -> int | None:
    if current is None:
        return None
    rows = (
        await session.execute(
            select(OpportunityScore)
            .where(OpportunityScore.opportunity_id == opportunity_id)
            .order_by(OpportunityScore.scored_at.desc())
            .limit(2)
        )
    ).scalars().all()
    if len(rows) < 2:
        return None
    return rows[1].value
