from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

OrganizationType = Literal["university", "college", "k12_district", "public_sector_education"]
MarketRole = Literal["target", "competitor"]
TrackingStatus = Literal["active", "inactive"]
PageCategory = Literal[
    "procurement",
    "technology",
    "digital_learning",
    "assessment",
    "funding",
    "leadership",
    "strategic_initiative",
    "partnership",
    "news",
]


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    organization_type: OrganizationType
    market_role: MarketRole
    state_code: str | None = None
    website_url: str = Field(min_length=1, max_length=500)

    @field_validator("name", "website_url")
    @classmethod
    def strip_required(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("must not be empty")
        return trimmed

    @field_validator("state_code")
    @classmethod
    def normalize_state(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip().upper()
        if not trimmed:
            return None
        if len(trimmed) != 2 or not trimmed.isalpha():
            raise ValueError("must be a two-letter USPS code")
        return trimmed


class OrganizationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    organization_type: OrganizationType | None = None
    market_role: MarketRole | None = None
    state_code: str | None = None
    website_url: str | None = Field(default=None, min_length=1, max_length=500)
    tracking_status: TrackingStatus | None = None

    @field_validator("name", "website_url")
    @classmethod
    def strip_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("must not be empty")
        return trimmed

    @field_validator("state_code")
    @classmethod
    def normalize_state(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip().upper()
        if not trimmed:
            return None
        if len(trimmed) != 2 or not trimmed.isalpha():
            raise ValueError("must be a two-letter USPS code")
        return trimmed


class OrganizationIpeds(BaseModel):
    content_layer: Literal["fact"] = "fact"
    source_name: str = "NCES IPEDS"
    source_url: str = "https://nces.ed.gov/ipeds/"
    unit_id: str | None = None
    collection_year: str | None = None
    release: Literal["final", "provisional"] | None = None
    attributes: list[dict] = Field(default_factory=list)


class OrganizationResponse(BaseModel):
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
    data_origin: Literal["live"] = "live"
    ipeds: OrganizationIpeds | None = None
    last_scan: dict | None = None


class OrganizationSourceCreate(BaseModel):
    url: str = Field(min_length=1, max_length=1000)
    page_category: PageCategory
    source_title: str | None = Field(default=None, max_length=200)

    @field_validator("url")
    @classmethod
    def strip_url(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("must not be empty")
        return trimmed

    @field_validator("source_title")
    @classmethod
    def strip_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None


class OrganizationSourceReject(BaseModel):
    status: Literal["rejected"]
    rejection_reason: str | None = Field(default=None, max_length=500)

    @field_validator("rejection_reason")
    @classmethod
    def strip_reason(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None
