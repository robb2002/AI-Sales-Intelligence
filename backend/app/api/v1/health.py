from fastapi import APIRouter

from app.schemas.auth import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def read_health() -> HealthResponse:
    return HealthResponse(status="ok")
