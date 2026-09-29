from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, require_app_user, require_roles
from app.core.security import CurrentUser
from app.schemas.scan_all_trigger import ScanAllTriggerResponse, ScanAllTriggerUpdate
from app.services import scan_all_trigger as trigger_service

router = APIRouter(tags=["scan-all-schedule"])

require_manager = require_roles("SALES_MANAGER")


@router.get("/scan-all-schedule", response_model=ScanAllTriggerResponse)
async def get_scan_all_schedule(
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[CurrentUser, Depends(require_app_user)],
) -> ScanAllTriggerResponse:
    return await trigger_service.get_schedule(session)


@router.patch("/scan-all-schedule", response_model=ScanAllTriggerResponse)
async def update_scan_all_schedule(
    body: ScanAllTriggerUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[CurrentUser, Depends(require_manager)],
) -> ScanAllTriggerResponse:
    return await trigger_service.set_schedule(session, body.scheduled_at)
