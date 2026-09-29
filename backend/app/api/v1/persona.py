from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.adapters.embeddings import get_embedding_adapter
from app.ai.adapters.gemini_persona import create_persona_llm
from app.api.deps import get_session, require_app_user
from app.core.config import get_settings
from app.core.security import CurrentUser
from app.schemas.persona import PersonaRequest, PersonaResponse
from app.services import persona as persona_service

router = APIRouter(tags=["persona"])


@router.post("/persona/messages", response_model=PersonaResponse)
async def send_persona_message(
    body: PersonaRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[CurrentUser, Depends(require_app_user)],
) -> PersonaResponse:
    settings = get_settings()
    return await persona_service.reply(
        session,
        settings=settings,
        llm=create_persona_llm(settings),
        embedder=get_embedding_adapter(settings),
        message=body.message,
        history=body.history,
        organization_id=body.organization_id,
        mode=body.mode,
        scope=body.scope,
    )
