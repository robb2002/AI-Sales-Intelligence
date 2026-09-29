from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, require_app_user
from app.core.security import CurrentUser
from app.schemas.trends import TrendsResponse
from app.services import trends as trends_service

router = APIRouter(tags=["trends"])


@router.get("/trends", response_model=TrendsResponse)
async def get_trends(
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[CurrentUser, Depends(require_app_user)],
    months: Annotated[int, Query()] = 6,
) -> TrendsResponse:
    return await trends_service.build_trends(session, months=months)
