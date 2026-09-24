from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, require_app_user
from app.core.errors import NotFoundError, ValidationAppError
from app.core.security import CurrentUser
from app.repositories.organization_sources import OrganizationSource, SOURCE_STATUSES
from app.repositories.organizations import Organization
from app.repositories.scans import ScanRun
from app.schemas.scans import (
    OrganizationSourceItem,
    OrganizationSourcePage,
    OrganizationSummary,
    ScanAllRequest,
    ScanBatchResponse,
    ScanDetail,
    ScanSourceResult,
    ScanSummary,
)
from app.services import scans as scan_service

router = APIRouter(tags=["organizations-scans"])


def _dt(value: datetime | None) -> datetime | None:
    return value


@router.get("/organizations", response_model=dict)
async def list_organizations(
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[CurrentUser, Depends(require_app_user)],
    tracking_status: Annotated[list[str] | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict:
    query = select(Organization)
    count_query = select(func.count()).select_from(Organization)
    if tracking_status:
        query = query.where(Organization.tracking_status.in_(tracking_status))
        count_query = count_query.where(Organization.tracking_status.in_(tracking_status))
    total = int(await session.scalar(count_query) or 0)
    rows = (
        await session.execute(query.order_by(Organization.name).limit(limit).offset(offset))
    ).scalars().all()

    # Latest finished scan per org for last_scanned_at
    data = []
    for org in rows:
        last = await session.scalar(
            select(ScanRun.finished_at)
            .where(
                ScanRun.organization_id == org.organization_id,
                ScanRun.finished_at.is_not(None),
            )
            .order_by(ScanRun.finished_at.desc())
            .limit(1)
        )
        data.append(
            OrganizationSummary(
                organization_id=org.organization_id,
                name=org.name,
                organization_type=org.organization_type,
                market_role=org.market_role,
                tracking_status=org.tracking_status,
                state_code=org.state_code,
                website_url=org.website_url,
                last_scanned_at=last,
            ).model_dump(mode="json")
        )
    return {"data": data, "total": total, "limit": limit, "offset": offset}


@router.get("/organizations/{organization_id}/sources", response_model=OrganizationSourcePage)
async def list_organization_sources(
    organization_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[CurrentUser, Depends(require_app_user)],
    status: Annotated[list[str] | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> OrganizationSourcePage:
    org = await session.get(Organization, organization_id)
    if org is None:
        raise NotFoundError("organization")

    query = select(OrganizationSource).where(
        OrganizationSource.organization_id == organization_id
    )
    count_query = (
        select(func.count())
        .select_from(OrganizationSource)
        .where(OrganizationSource.organization_id == organization_id)
    )
    if status:
        bad = [value for value in status if value not in SOURCE_STATUSES]
        if bad:
            raise ValidationAppError(message="Invalid status filter.", details={"status": "invalid"})
        query = query.where(OrganizationSource.status.in_(status))
        count_query = count_query.where(OrganizationSource.status.in_(status))

    total = int(await session.scalar(count_query) or 0)
    rows = (
        await session.execute(
            query.order_by(OrganizationSource.last_validated_at.desc())
            .limit(limit)
            .offset(offset)
        )
    ).scalars().all()

    return OrganizationSourcePage(
        data=[
            OrganizationSourceItem(
                organization_source_id=row.organization_source_id,
                organization_id=row.organization_id,
                url=row.url,
                source_title=row.source_title,
                page_category=row.page_category,
                status=row.status,
                extraction_status=row.extraction_status,
                is_official=row.is_official,
                rejection_reason=row.rejection_reason,
                last_validated_at=row.last_validated_at,
            )
            for row in rows
        ],
        total=total,
        limit=limit,
        offset=offset,
    )



@router.post("/scans", status_code=202)
async def start_scan_all(
    body: ScanAllRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[CurrentUser, Depends(require_app_user)],
) -> ScanBatchResponse:
    if body.scope != "all_tracked":
        raise ValidationAppError(message="scope must be all_tracked.", details={"scope": "invalid"})

    batch, runs, _started = await scan_service.start_scan_all(
        session,
        settings=request.app.state.settings,
        session_factory=request.app.state.session_factory,
    )
    org_names = await _org_names(session, [run.organization_id for run in runs])
    summaries = [_scan_summary(run, org_names.get(run.organization_id, "")) for run in runs]
    return ScanBatchResponse(
        batch_id=batch.batch_id,
        status=_batch_status(runs),
        scan_ids=[run.scan_id for run in runs],
        organization_count=len(runs),
        scans=summaries,
    )


@router.get("/scan-batches/{batch_id}")
async def get_scan_batch(
    batch_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[CurrentUser, Depends(require_app_user)],
) -> ScanBatchResponse:
    batch, runs, orgs = await scan_service.get_batch_detail(session, batch_id)
    names = {org.organization_id: org.name for org in orgs}
    summaries = [_scan_summary(run, names.get(run.organization_id, "")) for run in runs]
    return ScanBatchResponse(
        batch_id=batch.batch_id,
        status=_batch_status(runs),
        scan_ids=[run.scan_id for run in runs],
        organization_count=len(runs),
        scans=summaries,
    )


@router.get("/scans/{scan_id}", response_model=ScanDetail)
async def get_scan(
    scan_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[CurrentUser, Depends(require_app_user)],
) -> ScanDetail:
    run, org = await scan_service.get_scan_detail(session, scan_id)
    raw_sources = run.sources or []
    sources = [
        ScanSourceResult(
            source_name=item.get("source_name", "source"),
            status=item.get("status", "failed"),
            detail=item.get("detail"),
        )
        for item in raw_sources
        if isinstance(item, dict)
    ]
    return ScanDetail(
        scan_id=run.scan_id,
        organization_id=run.organization_id,
        organization_name=org.name,
        trigger=run.trigger,
        status=run.status,
        stage=run.stage,
        started_at=run.started_at,
        finished_at=run.finished_at,
        candidates_found=run.candidates_found,
        sources_approved=run.sources_approved,
        sources_rejected=run.sources_rejected,
        sources=sources,
        batch_id=run.batch_id,
        error_detail=run.error_detail,
        changes={},
    )


async def _org_names(session: AsyncSession, ids: list[UUID]) -> dict[UUID, str]:
    if not ids:
        return {}
    rows = (
        await session.execute(select(Organization).where(Organization.organization_id.in_(ids)))
    ).scalars().all()
    return {row.organization_id: row.name for row in rows}


def _scan_summary(run: ScanRun, name: str) -> ScanSummary:
    return ScanSummary(
        scan_id=run.scan_id,
        organization_id=run.organization_id,
        organization_name=name,
        trigger=run.trigger,
        status=run.status,
        stage=run.stage,
        started_at=run.started_at,
        finished_at=run.finished_at,
        candidates_found=run.candidates_found,
        sources_approved=run.sources_approved,
        sources_rejected=run.sources_rejected,
    )


def _batch_status(runs: list[ScanRun]) -> str:
    if not runs:
        return "failed"
    statuses = {run.status for run in runs}
    if statuses & {"queued", "running"}:
        return "running"
    if statuses == {"succeeded"}:
        return "succeeded"
    if statuses == {"failed"} or statuses == {"interrupted"}:
        return "failed"
    if "interrupted" in statuses and not (statuses & {"queued", "running"}):
        return "interrupted"
    return "partial"
