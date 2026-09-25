from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, require_app_user
from app.core.errors import NotFoundError, ValidationAppError
from app.core.security import CurrentUser
from app.repositories import evidence as evidence_repo
from app.repositories import opportunities as opportunities_repo
from app.repositories import signals as signals_repo
from app.repositories.organizations import Organization
from app.repositories.signals import SIGNAL_STATES, SIGNAL_TYPES, Signal
from app.repositories.sources import Source
from app.schemas.signals import (
    EvidenceItem,
    SignalAiSummary,
    SignalDetail,
    SignalPage,
    SignalSummary,
)

router = APIRouter(tags=["signals"])


@router.get("/signals", response_model=SignalPage)
async def list_signals(
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[CurrentUser, Depends(require_app_user)],
    organization_id: Annotated[UUID | None, Query()] = None,
    signal_type: Annotated[list[str] | None, Query()] = None,
    state: Annotated[list[str] | None, Query()] = None,
    q: Annotated[str | None, Query(max_length=200)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> SignalPage:
    if signal_type:
        bad = [t for t in signal_type if t not in SIGNAL_TYPES]
        if bad:
            raise ValidationAppError(message=f"Invalid signal_type: {bad[0]}")
    if state:
        bad_s = [s for s in state if s not in SIGNAL_STATES]
        if bad_s:
            raise ValidationAppError(message=f"Invalid state: {bad_s[0]}")

    rows, total = await signals_repo.list_signals(
        session,
        organization_id=organization_id,
        signal_types=signal_type,
        states=state,
        q=q,
        limit=limit,
        offset=offset,
    )
    counts = await evidence_repo.count_for_signals(
        session, [row.signal_id for row in rows]
    )
    org_names = await _org_names(session, {row.organization_id for row in rows})
    data = [
        _summary(row, org_names.get(row.organization_id, ""), counts.get(row.signal_id, 0))
        for row in rows
    ]
    return SignalPage(data=data, total=total, limit=limit, offset=offset)


@router.get("/signals/{signal_id}", response_model=SignalDetail)
async def get_signal(
    signal_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[CurrentUser, Depends(require_app_user)],
) -> SignalDetail:
    row = await session.get(Signal, signal_id)
    if row is None:
        raise NotFoundError("signal")
    org = await session.get(Organization, row.organization_id)
    org_name = org.name if org is not None else ""
    evidence_rows = await evidence_repo.list_for_signal(session, signal_id)
    evidence_items: list[EvidenceItem] = []
    for ev in evidence_rows:
        source_name = org_name
        if ev.source_id is not None:
            source = await session.get(Source, ev.source_id)
            if source is not None:
                source_name = source.name
        elif org is not None:
            source_name = f"{org.name} official website"
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
    summary = _summary(row, org_name, len(evidence_items))
    ai_summary = None
    if row.ai_summary:
        ai_summary = SignalAiSummary(
            text=row.ai_summary,
            evidence_ids=[item.evidence_id for item in evidence_items],
        )
    opp_map = await opportunities_repo.opportunity_ids_for_signals(
        session, [row.signal_id]
    )
    return SignalDetail(
        **summary.model_dump(),
        rejection_reason=row.rejection_reason,
        opportunity_ids=opp_map.get(row.signal_id, []),
        ai_summary=ai_summary,
        evidence=evidence_items,
    )


def _summary(row: Signal, organization_name: str, source_count: int) -> SignalSummary:
    return SignalSummary(
        signal_id=row.signal_id,
        organization_id=row.organization_id,
        organization_name=organization_name,
        signal_type=row.signal_type,
        state=row.state,
        title=row.title,
        summary=row.summary,
        date=row.published_on,
        date_status="available" if row.published_on else "unavailable",
        source_count=source_count,
        data_origin=row.data_origin,
    )


async def _org_names(session: AsyncSession, org_ids: set) -> dict:
    if not org_ids:
        return {}
    from sqlalchemy import select

    rows = (
        await session.execute(
            select(Organization).where(Organization.organization_id.in_(org_ids))
        )
    ).scalars().all()
    return {row.organization_id: row.name for row in rows}
