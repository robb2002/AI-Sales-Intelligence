from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

PersonaMode = Literal["auto", "email", "call_prep", "competitor", "daily_briefing", "research"]


class PersonaHistoryTurn(BaseModel):
    role: Literal["user", "assistant"]
    text: str = Field(max_length=4000)


class PersonaRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    history: list[PersonaHistoryTurn] = Field(default_factory=list, max_length=12)
    organization_id: UUID | None = None
    mode: PersonaMode = "auto"
    # organization: only the selected organization's data, Advisor-style (needs organization_id).
    # general: outside/portfolio data, never scoped to one organization.
    # auto: detect an organization from the message (older behaviour).
    scope: Literal["auto", "organization", "general"] = "auto"


class PersonaBulletItem(BaseModel):
    text: str
    layer: str | None = None
    refs: list[int] = Field(default_factory=list)


class PersonaBlock(BaseModel):
    type: Literal["heading", "paragraph", "bullets", "email"]
    text: str | None = None
    layer: str | None = None
    refs: list[int] = Field(default_factory=list)
    items: list[PersonaBulletItem] = Field(default_factory=list)
    subject: str | None = None
    body: str | None = None


class PersonaAnswer(BaseModel):
    text: str
    blocks: list[PersonaBlock] = Field(default_factory=list)


class PersonaSource(BaseModel):
    ref: int
    label: str
    url: str | None = None
    kind: Literal["stored_evidence", "official_website", "live_lookup", "system_data"]
    snippet: str | None = None


class PersonaUsed(BaseModel):
    organizations: list[str] = Field(default_factory=list)
    live_lookup: bool = False


class PersonaResponse(BaseModel):
    status: Literal["answered", "unavailable"]
    answer: PersonaAnswer
    sources: list[PersonaSource] = Field(default_factory=list)
    follow_ups: list[str] = Field(default_factory=list)
    used: PersonaUsed
    data_origin: str = "live"
