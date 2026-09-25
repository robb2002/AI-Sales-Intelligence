from fastapi import APIRouter, Depends

from app.api.deps import require_app_user
from app.api.v1 import advisor, health, me, opportunities, organizations, scans, signals

public_router = APIRouter(prefix="/api/v1")
public_router.include_router(health.router)

# Every router added here requires a verified Clerk session and an application role.
protected_router = APIRouter(prefix="/api/v1", dependencies=[Depends(require_app_user)])
protected_router.include_router(me.router)
protected_router.include_router(organizations.router)
protected_router.include_router(scans.router)
protected_router.include_router(signals.router)
protected_router.include_router(opportunities.router)
protected_router.include_router(advisor.router)
