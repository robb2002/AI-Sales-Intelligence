from __future__ import annotations

from datetime import date as Date
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    evidence_id: UUID
    source_name: str
    source_url: str
    date: Date | None = None
    date_status: str
    snippet: str
    relationship: str
    relationship_layer: str = "interpretation"
    data_origin: str
    retrieved_at: datetime


class SignalSummary(BaseModel):
    signal_id: UUID
    organization_id: UUID
    organization_name: str
    signal_type: str
    state: str
    title: str
    summary: str
    summary_layer: str = "fact"
    date: Date | None = None
    date_status: str
    source_count: int = 0
    data_origin: str


class SignalAiSummary(BaseModel):
    text: str
    content_layer: str = "interpretation"
    evidence_ids: list[UUID] = Field(default_factory=list)


class SignalDetail(SignalSummary):
    rejection_reason: str | None = None
    opportunity_ids: list[UUID] = Field(default_factory=list)
    ai_summary: SignalAiSummary | None = None
    evidence: list[EvidenceItem] = Field(default_factory=list)


class SignalPage(BaseModel):
    data: list[SignalSummary]
    total: int
    limit: int
    offset: int
