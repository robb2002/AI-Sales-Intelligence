import uuid
from typing import Literal

from pydantic import BaseModel

Role = Literal["SALES_REP", "SALES_MANAGER"]


class CurrentUserResponse(BaseModel):
    user_id: uuid.UUID
    clerk_user_id: str
    email: str
    role: Role


class HealthResponse(BaseModel):
    status: Literal["ok"]
