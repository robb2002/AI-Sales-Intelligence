from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.adapters.azure_openai import create_llm_adapter
from app.api.deps import get_session, require_app_user
from app.core.config import get_settings
from app.core.errors import NotFoundError
from app.core.security import CurrentUser
from app.repositories.organizations import Organization
from app.schemas.peer_competitors import PeerCompetitorsResponse
from app.services import peer_competitors as peer_service

router = APIRouter(tags=["peer-competitors"])


async def _organization(session: AsyncSession, organization_id: UUID) -> Organization:
    org = await session.get(Organization, organization_id)
    if org is None:
        raise NotFoundError("organization")
    return org


@router.get(
    "/organizations/{organization_id}/peer-competitors", response_model=PeerCompetitorsResponse
)
async def get_peer_competitors(
    organization_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[CurrentUser, Depends(require_app_user)],
) -> PeerCompetitorsResponse:
    org = await _organization(session, organization_id)
    return await peer_service.get_saved(session, settings=get_settings(), org=org)


@router.post(
    "/organizations/{organization_id}/peer-competitors/refresh",
    response_model=PeerCompetitorsResponse,
)
async def refresh_peer_competitors(
    organization_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[CurrentUser, Depends(require_app_user)],
) -> PeerCompetitorsResponse:
    org = await _organization(session, organization_id)
    settings = get_settings()
    return await peer_service.refresh(
        session, settings=settings, llm=create_llm_adapter(settings), org=org
    )
