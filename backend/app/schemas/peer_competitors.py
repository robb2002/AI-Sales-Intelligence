from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class PeerCompetitorItem(BaseModel):
    rank: int
    name: str
    source_title: str | None = None
    source_url: str
    snippet: str
    retrieved_at: datetime


class PeerCompetitorsResponse(BaseModel):
    organization_id: UUID
    configured: bool
    last_updated_at: datetime | None = None
    search_query: str | None = None
    data_origin: str = "live"
    peers: list[PeerCompetitorItem] = Field(default_factory=list)
