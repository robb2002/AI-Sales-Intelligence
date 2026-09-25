from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.signals import EvidenceItem, SignalSummary


class ScoreFactor(BaseModel):
    key: str
    points: int
    max_points: int


class ScoreExplanation(BaseModel):
    text: str
    content_layer: str = "interpretation"
    evidence_ids: list[UUID] = Field(default_factory=list)


class ScorePayload(BaseModel):
    value: int
    band: str
    weight_version: str
    factors: list[ScoreFactor]
    explanation: ScoreExplanation | None = None
    explanation_status: str
    previous_value: int | None = None
    scored_at: datetime | None = None


class CorrelationPayload(BaseModel):
    text: str
    content_layer: str = "interpretation"
    evidence_ids: list[UUID] = Field(default_factory=list)


class RecommendedActionPayload(BaseModel):
    text: str
    content_layer: str = "recommended_action"
    evidence_ids: list[UUID] = Field(default_factory=list)


class OpportunitySummary(BaseModel):
    opportunity_id: UUID
    organization_id: UUID
    organization_name: str
    organization_type: str
    state_code: str | None
    score: ScorePayload
    signal_count: int = 0
    updated_at: datetime
    data_origin: str


class OpportunityDetail(OpportunitySummary):
    label: str = "potential_opportunity"
    signals: list[SignalSummary] = Field(default_factory=list)
    correlation: CorrelationPayload
    recommended_action: RecommendedActionPayload | None = None
    evidence: list[EvidenceItem] = Field(default_factory=list)


class OpportunityPage(BaseModel):
    data: list[OpportunitySummary]
    total: int
    limit: int
    offset: int
