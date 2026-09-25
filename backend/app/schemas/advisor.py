from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.signals import EvidenceItem


class AdvisorQuestionRequest(BaseModel):
    scope_type: str
    scope_id: UUID
    message: str = Field(min_length=1, max_length=2000)
    session_id: UUID | None = None


class AdvisorSegment(BaseModel):
    text: str
    content_layer: str
    evidence_ids: list[UUID] = Field(default_factory=list)


class AdvisorAnswerBody(BaseModel):
    text: str
    segments: list[AdvisorSegment] = Field(default_factory=list)


class AdvisorAnswerResponse(BaseModel):
    session_id: UUID
    scope_type: str
    scope_id: UUID
    advisor_status: str
    answer: AdvisorAnswerBody
    evidence: list[EvidenceItem] = Field(default_factory=list)
    data_origin: str = "live"


class AdvisorTurnUser(BaseModel):
    role: str = "user"
    text: str
    created_at: datetime


class AdvisorTurnAdvisor(BaseModel):
    role: str = "advisor"
    answer: AdvisorAnswerBody
    advisor_status: str
    evidence: list[EvidenceItem] = Field(default_factory=list)
    created_at: datetime


class AdvisorSessionResponse(BaseModel):
    session_id: UUID
    scope_type: str
    scope_id: UUID
    turns: list[AdvisorTurnUser | AdvisorTurnAdvisor] = Field(default_factory=list)
