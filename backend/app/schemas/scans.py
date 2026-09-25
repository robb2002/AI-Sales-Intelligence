from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class OrganizationSummary(BaseModel):
    organization_id: UUID
    name: str
    organization_type: str
    market_role: str
    tracking_status: str
    state_code: str | None
    website_url: str | None
    signal_count: int = 0
    opportunity_count: int = 0
    last_scanned_at: datetime | None = None


class OrganizationSourceItem(BaseModel):
    organization_source_id: UUID
    organization_id: UUID
    url: str
    source_title: str | None
    page_category: str
    status: str
    extraction_status: str
    document_count: int = 0
    is_official: bool
    rejection_reason: str | None
    last_validated_at: datetime


class PageMeta(BaseModel):
    data: list
    total: int
    limit: int
    offset: int


class OrganizationSourcePage(BaseModel):
    data: list[OrganizationSourceItem]
    total: int
    limit: int
    offset: int


class ScanSourceResult(BaseModel):
    source_name: str
    status: str
    detail: str | None = None


class ScanSummary(BaseModel):
    scan_id: UUID
    batch_id: UUID | None = None
    organization_id: UUID
    organization_name: str
    trigger: str
    requested_by_email: str | None = None
    status: str
    stage: str | None
    started_at: datetime | None
    finished_at: datetime | None
    candidates_found: int = 0
    sources_approved: int = 0
    sources_rejected: int = 0
    documents_collected: int = 0
    joined_existing: bool = False


class ScanSummaryPage(BaseModel):
    data: list[ScanSummary]
    total: int
    limit: int
    offset: int


class ScanDetail(ScanSummary):
    sources: list[ScanSourceResult] = Field(default_factory=list)
    error_detail: str | None = None
    changes: dict = Field(default_factory=dict)


class ScanAllRequest(BaseModel):
    scope: str


class ScanBatchResponse(BaseModel):
    batch_id: UUID
    status: str
    scan_ids: list[UUID]
    organization_count: int
    scans: list[ScanSummary] = Field(default_factory=list)
