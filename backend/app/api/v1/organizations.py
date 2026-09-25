from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, require_roles
from app.core.errors import ValidationAppError
from app.core.security import CurrentUser
from app.repositories import documents as documents_repo
from app.repositories.organizations import ORGANIZATION_TYPES, TRACKING_STATUSES
from app.schemas.organizations import (
    OrganizationCreate,
    OrganizationResponse,
    OrganizationSourceCreate,
    OrganizationSourceReject,
    OrganizationUpdate,
)
from app.schemas.scans import OrganizationSourceItem
from app.services import organization_page_sources as page_source_service
from app.services import organizations as org_service

router = APIRouter(tags=["organizations"])

require_manager = require_roles("SALES_MANAGER")


@router.get("/organizations")
async def list_organizations(
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[CurrentUser, Depends(require_roles("SALES_REP", "SALES_MANAGER"))],
    q: Annotated[str | None, Query(max_length=200)] = None,
    organization_type: Annotated[list[str] | None, Query()] = None,
    state_code: Annotated[list[str] | None, Query()] = None,
    tracking_status: Annotated[list[str] | None, Query()] = None,
    sort: Annotated[str, Query()] = "name",
    direction: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict:
    if organization_type and any(value not in ORGANIZATION_TYPES for value in organization_type):
        raise ValidationAppError(details={"organization_type": "invalid"})
    if tracking_status and any(value not in TRACKING_STATUSES for value in tracking_status):
        raise ValidationAppError(details={"tracking_status": "invalid"})
    if sort not in ("name", "recently_scanned"):
        raise ValidationAppError(details={"sort": "invalid"})
    if direction is None:
        direction = "desc" if sort == "recently_scanned" else "asc"
    if direction not in ("asc", "desc"):
        raise ValidationAppError(details={"direction": "invalid"})

    rows, total = await org_service.list_organizations(
        session,
        q=q,
        organization_types=organization_type,
        state_codes=state_code,
        tracking_statuses=tracking_status,
        sort=sort,
        direction=direction,
        limit=limit,
        offset=offset,
    )
    return {
        "data": [row.model_dump(mode="json") for row in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/organizations/{organization_id}", response_model=OrganizationResponse)
async def get_organization(
    organization_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[CurrentUser, Depends(require_roles("SALES_REP", "SALES_MANAGER"))],
) -> OrganizationResponse:
    return await org_service.get_organization(session, organization_id)


@router.post("/organizations", response_model=OrganizationResponse, status_code=201)
async def create_organization(
    body: OrganizationCreate,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[CurrentUser, Depends(require_manager)],
) -> OrganizationResponse:
    return await org_service.create_organization(
        session, body, settings=request.app.state.settings
    )


@router.patch("/organizations/{organization_id}", response_model=OrganizationResponse)
async def update_organization(
    organization_id: UUID,
    body: OrganizationUpdate,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[CurrentUser, Depends(require_manager)],
) -> OrganizationResponse:
    return await org_service.update_organization(
        session, organization_id, body, settings=request.app.state.settings
    )


@router.post(
    "/organizations/{organization_id}/sources",
    response_model=OrganizationSourceItem,
    status_code=201,
)
async def add_organization_source(
    organization_id: UUID,
    body: OrganizationSourceCreate,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[CurrentUser, Depends(require_manager)],
) -> OrganizationSourceItem:
    row = await page_source_service.add_organization_page_source(
        session,
        organization_id,
        url=body.url,
        page_category=body.page_category,
        source_title=body.source_title,
        settings=request.app.state.settings,
    )
    counts = await documents_repo.count_by_organization_source(
        session, [row.organization_source_id]
    )
    return OrganizationSourceItem(
        organization_source_id=row.organization_source_id,
        organization_id=row.organization_id,
        url=row.url,
        source_title=row.source_title,
        page_category=row.page_category,
        status=row.status,
        extraction_status=row.extraction_status,
        document_count=counts.get(row.organization_source_id, 0),
        is_official=row.is_official,
        rejection_reason=row.rejection_reason,
        last_validated_at=row.last_validated_at,
    )


@router.patch(
    "/organizations/{organization_id}/sources/{organization_source_id}",
    response_model=OrganizationSourceItem,
)
async def reject_organization_source(
    organization_id: UUID,
    organization_source_id: UUID,
    body: OrganizationSourceReject,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[CurrentUser, Depends(require_manager)],
) -> OrganizationSourceItem:
    row = await page_source_service.reject_organization_page_source(
        session,
        organization_id,
        organization_source_id,
        rejection_reason=body.rejection_reason,
    )
    counts = await documents_repo.count_by_organization_source(
        session, [row.organization_source_id]
    )
    return OrganizationSourceItem(
        organization_source_id=row.organization_source_id,
        organization_id=row.organization_id,
        url=row.url,
        source_title=row.source_title,
        page_category=row.page_category,
        status=row.status,
        extraction_status=row.extraction_status,
        document_count=counts.get(row.organization_source_id, 0),
        is_official=row.is_official,
        rejection_reason=row.rejection_reason,
        last_validated_at=row.last_validated_at,
    )
