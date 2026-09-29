from __future__ import annotations

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, require_app_user
from app.ai.adapters import create_llm_adapter
from app.core.config import get_settings
from app.core.errors import NotFoundError, ValidationAppError
from app.core.security import CurrentUser
from app.repositories import opportunities as opportunities_repo
from app.repositories.evidence import Evidence
from app.repositories.opportunities import Opportunity, OpportunitySignal
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
from app.services.opportunity_correlation import ensure_recommended_action

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
    found_opportunity = (
        await session.execute(
            select(Opportunity, Organization)
            .outerjoin(Organization, Organization.organization_id == Opportunity.organization_id)
            .where(Opportunity.opportunity_id == opportunity_id)
        )
    ).first()
    if found_opportunity is None:
        raise NotFoundError("opportunity")
    opportunity, organization = found_opportunity
    if organization is None:
        raise NotFoundError("organization")

    # Latest and previous score in one query (newest first).
    recent_scores = (
        await session.execute(
            select(OpportunityScore)
            .where(OpportunityScore.opportunity_id == opportunity_id)
            .order_by(OpportunityScore.scored_at.desc())
            .limit(2)
        )
    ).scalars().all()
    score = recent_scores[0] if recent_scores else None
    previous = recent_scores[1].value if len(recent_scores) > 1 else None

    signal_rows = list(
        (
            await session.execute(
                select(Signal)
                .join(OpportunitySignal, OpportunitySignal.signal_id == Signal.signal_id)
                .where(OpportunitySignal.opportunity_id == opportunity_id)
            )
        ).scalars().all()
    )
    signal_ids = [row.signal_id for row in signal_rows]

    evidence_by_signal: dict[UUID, list[tuple]] = {}
    if signal_ids:
        found_evidence = await session.execute(
            select(Evidence, Source.name)
            .outerjoin(Source, Source.source_id == Evidence.source_id)
            .where(Evidence.signal_id.in_(signal_ids))
            .order_by(Evidence.created_at)
        )
        for ev, joined_source_name in found_evidence.all():
            evidence_by_signal.setdefault(ev.signal_id, []).append((ev, joined_source_name))

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
            source_count=len(evidence_by_signal.get(row.signal_id, [])),
            data_origin=row.data_origin,
        )
        for row in signal_rows
    ]

    evidence_items: list[EvidenceItem] = []
    evidence_ids: list[UUID] = []
    for sid in signal_ids:
        for ev, joined_source_name in evidence_by_signal.get(sid, []):
            if ev.source_id is not None:
                source_name = joined_source_name or organization.name
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

    # Backfill §27 for opportunities created before recommend was wired (one LLM call).
    if not opportunity.recommended_action_text and signal_rows and score is not None:
        settings = get_settings()
        if settings.llm_configured:
            await ensure_recommended_action(
                session,
                create_llm_adapter(settings),
                opportunity=opportunity,
                org=organization,
                score_value=score.value,
                score_band=score.band,
                signals=signal_rows,
            )
            if opportunity.recommended_action_text:
                await session.commit()

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
