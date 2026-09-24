from fastapi import APIRouter

from app.api.deps import CurrentUserDep
from app.schemas.auth import CurrentUserResponse

router = APIRouter(tags=["auth"])


@router.get("/me", response_model=CurrentUserResponse)
async def read_current_user(user: CurrentUserDep) -> CurrentUserResponse:
    return CurrentUserResponse(
        user_id=user.user_id,
        clerk_user_id=user.clerk_user_id,
        email=user.email,
        role=user.role,
    )
