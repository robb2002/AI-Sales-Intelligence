from fastapi import APIRouter, Depends

from app.api.deps import require_app_user
from app.api.v1 import health, me

public_router = APIRouter(prefix="/api/v1")
public_router.include_router(health.router)

# Every router added here requires a verified Clerk session and an application role.
protected_router = APIRouter(prefix="/api/v1", dependencies=[Depends(require_app_user)])
protected_router.include_router(me.router)
