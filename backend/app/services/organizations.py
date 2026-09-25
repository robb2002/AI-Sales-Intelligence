from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import ConflictError, NotFoundError, ValidationAppError
from app.repositories.opportunities import Opportunity
from app.repositories.organizations import (
    MARKET_ROLES,
    ORGANIZATION_TYPES,
    TRACKING_STATUSES,
    Organization,
)
from app.repositories.scans import ScanRun
from app.repositories.signals import Signal
from app.schemas.organizations import (
    OrganizationCreate,
    OrganizationIpeds,
    OrganizationResponse,
    OrganizationUpdate,
)
from app.services.organization_website import validate_official_website


async def list_organizations(
    session: AsyncSession,
    *,
    q: str | None = None,
    organization_types: list[str] | None = None,
    state_codes: list[str] | None = None,
    tracking_statuses: list[str] | None = None,
    sort: str = "name",
    direction: str = "asc",
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[OrganizationResponse], int]:
    if q is not None and len(q.strip()) < 2:
        return [], 0

    filters = []
    if q and q.strip():
        filters.append(Organization.name.ilike(f"%{q.strip()}%"))
    if organization_types:
        filters.append(Organization.organization_type.in_(organization_types))
    if state_codes:
        filters.append(Organization.state_code.in_([code.upper() for code in state_codes]))
    if tracking_statuses:
        filters.append(Organization.tracking_status.in_(tracking_statuses))

    count_query = select(func.count()).select_from(Organization)
    query = select(Organization)
    for clause in filters:
        count_query = count_query.where(clause)
        query = query.where(clause)

    total = int(await session.scalar(count_query) or 0)

    if sort == "recently_scanned":
        last_scan = (
            select(
                ScanRun.organization_id,
                func.max(ScanRun.finished_at).label("last_finished"),
            )
            .where(ScanRun.finished_at.is_not(None))
            .group_by(ScanRun.organization_id)
            .subquery()
        )
        query = query.outerjoin(
            last_scan, last_scan.c.organization_id == Organization.organization_id
        )
        order_col = last_scan.c.last_finished
        query = query.order_by(
            order_col.desc().nullslast() if direction == "desc" else order_col.asc().nullslast(),
            Organization.name.asc(),
        )
    else:
        query = query.order_by(
            Organization.name.desc() if direction == "desc" else Organization.name.asc()
        )

    rows = (await session.execute(query.limit(limit).offset(offset))).scalars().all()
    responses = [await _to_response(session, org, include_detail=False) for org in rows]
    return responses, total


async def get_organization(
    session: AsyncSession, organization_id: uuid.UUID
) -> OrganizationResponse:
    org = await session.get(Organization, organization_id)
    if org is None:
        raise NotFoundError("organization")
    return await _to_response(session, org, include_detail=True)


async def create_organization(
    session: AsyncSession,
    body: OrganizationCreate,
    *,
    settings: Settings,
) -> OrganizationResponse:
    validated = await validate_official_website(body.website_url, settings)
    existing = await session.scalar(
        select(Organization).where(Organization.website_url == validated.final_url)
    )
    if existing is not None:
        raise ConflictError("website_url", "An organization with this website already exists.")

    org = Organization(
        name=body.name,
        organization_type=body.organization_type,
        market_role=body.market_role,
        tracking_status="inactive",
        state_code=body.state_code,
        website_url=validated.final_url,
    )
    session.add(org)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError("website_url", "An organization with this website already exists.") from exc
    await session.refresh(org)
    return await _to_response(session, org, include_detail=True)


async def update_organization(
    session: AsyncSession,
    organization_id: uuid.UUID,
    body: OrganizationUpdate,
    *,
    settings: Settings,
) -> OrganizationResponse:
    org = await session.get(Organization, organization_id)
    if org is None:
        raise NotFoundError("organization")

    payload = body.model_dump(exclude_unset=True)
    if not payload:
        raise ValidationAppError(
            message="Provide at least one field to update.",
            details={"body": "empty"},
        )

    if "name" in payload and payload["name"] is not None:
        org.name = payload["name"]
    if "organization_type" in payload and payload["organization_type"] is not None:
        if payload["organization_type"] not in ORGANIZATION_TYPES:
            raise ValidationAppError(details={"organization_type": "invalid"})
        org.organization_type = payload["organization_type"]
    if "market_role" in payload and payload["market_role"] is not None:
        if payload["market_role"] not in MARKET_ROLES:
            raise ValidationAppError(details={"market_role": "invalid"})
        org.market_role = payload["market_role"]
    if "tracking_status" in payload and payload["tracking_status"] is not None:
        if payload["tracking_status"] not in TRACKING_STATUSES:
            raise ValidationAppError(details={"tracking_status": "invalid"})
        org.tracking_status = payload["tracking_status"]
    if "state_code" in payload:
        org.state_code = payload["state_code"]

    if "website_url" in payload and payload["website_url"] is not None:
        if payload["website_url"] != org.website_url:
            validated = await validate_official_website(payload["website_url"], settings)
            duplicate = await session.scalar(
                select(Organization).where(
                    Organization.website_url == validated.final_url,
                    Organization.organization_id != organization_id,
                )
            )
            if duplicate is not None:
                raise ConflictError(
                    "website_url", "An organization with this website already exists."
                )
            org.website_url = validated.final_url

    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError("website_url", "An organization with this website already exists.") from exc
    await session.refresh(org)
    return await _to_response(session, org, include_detail=True)


async def _to_response(
    session: AsyncSession, org: Organization, *, include_detail: bool
) -> OrganizationResponse:
    last_scanned_at = await session.scalar(
        select(ScanRun.finished_at)
        .where(
            ScanRun.organization_id == org.organization_id,
            ScanRun.finished_at.is_not(None),
        )
        .order_by(ScanRun.finished_at.desc())
        .limit(1)
    )

    signal_count = int(
        await session.scalar(
            select(func.count())
            .select_from(Signal)
            .where(
                Signal.organization_id == org.organization_id,
                Signal.state.in_(("validated", "merged")),
            )
        )
        or 0
    )
    opportunity_count = int(
        await session.scalar(
            select(func.count())
            .select_from(Opportunity)
            .where(Opportunity.organization_id == org.organization_id)
        )
        or 0
    )

    ipeds = None
    last_scan = None
    if include_detail:
        if org.ipeds_unit_id or org.ipeds_collection_year or org.ipeds_release:
            attrs = org.ipeds_attributes if isinstance(org.ipeds_attributes, list) else []
            ipeds = OrganizationIpeds(
                unit_id=org.ipeds_unit_id,
                collection_year=org.ipeds_collection_year,
                release=org.ipeds_release if org.ipeds_release in ("final", "provisional") else None,
                source_url=org.ipeds_source_url or "https://nces.ed.gov/ipeds/",
                attributes=attrs if isinstance(attrs, list) else [],
            )
        last_run = (
            await session.execute(
                select(ScanRun)
                .where(ScanRun.organization_id == org.organization_id)
                .order_by(ScanRun.started_at.desc().nullslast())
                .limit(1)
            )
        ).scalar_one_or_none()
        if last_run is not None:
            last_scan = {
                "scan_id": str(last_run.scan_id),
                "organization_id": str(last_run.organization_id),
                "organization_name": org.name,
                "status": last_run.status,
                "stage": last_run.stage,
                "trigger": last_run.trigger,
                "started_at": last_run.started_at.isoformat().replace("+00:00", "Z")
                if last_run.started_at
                else None,
                "finished_at": last_run.finished_at.isoformat().replace("+00:00", "Z")
                if last_run.finished_at
                else None,
                "joined_existing": False,
                "data_origin": "live",
            }

    return OrganizationResponse(
        organization_id=org.organization_id,
        name=org.name,
        organization_type=org.organization_type,
        market_role=org.market_role,
        tracking_status=org.tracking_status,
        state_code=org.state_code,
        website_url=org.website_url,
        signal_count=signal_count,
        opportunity_count=opportunity_count,
        last_scanned_at=last_scanned_at,
        data_origin="live",
        ipeds=ipeds,
        last_scan=last_scan,
    )
