from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.signals import EvidenceItem, SignalSummary


class CompetitorSignal(SignalSummary):
    evidence: list[EvidenceItem] = Field(default_factory=list)


class CompetitorEntry(BaseModel):
    organization_id: UUID
    name: str
    website_url: str | None = None
    tracking_status: str
    last_scanned_at: datetime | None = None
    validated_signal_count: int
    signals: list[CompetitorSignal] = Field(default_factory=list)


class CompetitorTotals(BaseModel):
    competitors: int
    validated_signals: int
    new_in_window: int
    window_days: int


class CompetitorsResponse(BaseModel):
    generated_at: datetime
    data_origin: str
    totals: CompetitorTotals
    competitors: list[CompetitorEntry]
