from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, require_app_user
from app.core.security import CurrentUser
from app.schemas.competitors import CompetitorsResponse
from app.services import competitors as competitors_service

router = APIRouter(tags=["competitors"])


@router.get("/competitors", response_model=CompetitorsResponse)
async def get_competitors(
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[CurrentUser, Depends(require_app_user)],
) -> CompetitorsResponse:
    return await competitors_service.build_competitors(session)
