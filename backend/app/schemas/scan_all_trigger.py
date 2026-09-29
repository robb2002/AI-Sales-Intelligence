from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, field_validator


class ScanAllTriggerResponse(BaseModel):
    scheduled_at: datetime | None = None


class ScanAllTriggerUpdate(BaseModel):
    # Send null to clear an existing schedule.
    scheduled_at: datetime | None = None

    @field_validator("scheduled_at")
    @classmethod
    def must_be_future(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        aware = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
        if aware <= datetime.now(timezone.utc):
            raise ValueError("must be a future date and time")
        return aware
