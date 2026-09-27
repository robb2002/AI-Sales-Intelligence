from __future__ import annotations

from datetime import date as Date
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.opportunities import OpportunitySummary
from app.schemas.signals import EvidenceItem, SignalSummary


class DashboardOpportunities(BaseModel):
    total: int
    by_band: dict[str, int]
    new_since: datetime
    new_count: int


class DashboardSignals(BaseModel):
    validated_total: int
    by_type: dict[str, int]
    recent_window_days: int
    recent_count: int


class DashboardCompetitorVendor(BaseModel):
    validated_total: int
    new_in_window: int


class DashboardScanStatus(BaseModel):
    state: str
    last_finished_at: datetime | None = None
    running: bool
    last_status: str | None = None
    sources_failed: int


class SignalVolumePoint(BaseModel):
    date: Date
    count: int


class DashboardInsight(BaseModel):
    text: str
    content_layer: str = "interpretation"
    evidence_ids: list[UUID] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)


class DashboardResponse(BaseModel):
    generated_at: datetime
    data_origin: str
    opportunities: DashboardOpportunities
    signals: DashboardSignals
    competitor_vendor: DashboardCompetitorVendor
    scan_status: DashboardScanStatus
    prioritized_opportunities: list[OpportunitySummary]
    recent_signals: list[SignalSummary]
    signal_volume: list[SignalVolumePoint]
    ai_insights: list[DashboardInsight]
