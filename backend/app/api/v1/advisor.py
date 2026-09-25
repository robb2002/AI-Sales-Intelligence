from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.adapters.azure_openai import create_llm_adapter
from app.ai.adapters.embeddings import get_embedding_adapter
from app.api.deps import get_session, require_app_user
from app.core.config import get_settings
from app.core.security import CurrentUser
from app.schemas.advisor import AdvisorAnswerResponse, AdvisorQuestionRequest, AdvisorSessionResponse
from app.services import advisor as advisor_service

router = APIRouter(tags=["advisor"])


@router.post("/advisor/questions", response_model=AdvisorAnswerResponse)
async def ask_advisor(
    body: AdvisorQuestionRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[CurrentUser, Depends(require_app_user)],
) -> AdvisorAnswerResponse:
    settings = get_settings()
    llm = create_llm_adapter(settings)
    embedder = get_embedding_adapter(settings)
    return await advisor_service.ask(
        session,
        settings=settings,
        llm=llm,
        embedder=embedder,
        scope_type=body.scope_type,
        scope_id=body.scope_id,
        message=body.message,
        session_id=body.session_id,
    )


@router.get("/advisor/sessions/{session_id}", response_model=AdvisorSessionResponse)
async def get_advisor_session(
    session_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[CurrentUser, Depends(require_app_user)],
) -> AdvisorSessionResponse:
    return await advisor_service.get_session_payload(session, session_id)
