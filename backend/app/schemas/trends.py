from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field


class TrendsWindow(BaseModel):
    months: int
    date_from: date
    date_to: date


class TrendsTotals(BaseModel):
    signals: int
    undated: int
    organizations: int


class TrendsSignalTypeMonth(BaseModel):
    month: str
    counts: dict[str, int]


class TrendsBucket(BaseModel):
    organizations: int
    total: int
    undated: int
    by_month: list[int] = Field(default_factory=list)


class TrendsStateBucket(TrendsBucket):
    state_code: str | None


class TrendsOrganizationTypeBucket(TrendsBucket):
    organization_type: str


class TrendsResponse(BaseModel):
    generated_at: datetime
    data_origin: str
    window: TrendsWindow
    month_keys: list[str]
    totals: TrendsTotals
    by_signal_type: list[TrendsSignalTypeMonth]
    by_state: list[TrendsStateBucket]
    by_organization_type: list[TrendsOrganizationTypeBucket]
