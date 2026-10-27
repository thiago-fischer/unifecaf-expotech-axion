from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.product_schema import PositiveInteger

_IDENTIFIER_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._:-]*$"
DeviceIdentifier = Annotated[
    str, Field(strict=True, min_length=1, max_length=64, pattern=_IDENTIFIER_PATTERN)
]
EventIdentifier = Annotated[
    str, Field(strict=True, min_length=1, max_length=64, pattern=_IDENTIFIER_PATTERN)
]
UnitIdentifier = Annotated[
    str, Field(strict=True, min_length=1, max_length=128, pattern=_IDENTIFIER_PATTERN)
]


class ProgressStatus(StrEnum):
    STARTED = "started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class ProgressEventCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    device_id: DeviceIdentifier
    event_id: EventIdentifier
    unit_id: UnitIdentifier
    product_id: PositiveInteger
    status: ProgressStatus
    step_sequence: PositiveInteger | None = None
    message: Annotated[str, Field(strict=True, max_length=500)] | None = None
    occurred_at: datetime | None = None

    @field_validator("occurred_at")
    @classmethod
    def require_timezone_and_normalize(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.utcoffset() is None:
            raise ValueError("occurred_at deve incluir fuso horário.")
        return value.astimezone(UTC)


class ProgressEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    product_id: int
    device_id: str
    event_id: str
    unit_id: str
    status: ProgressStatus
    step_sequence: int | None
    message: str | None
    occurred_at: datetime | None
    received_at: datetime

    @field_validator("occurred_at", "received_at", mode="before")
    @classmethod
    def normalize_sqlite_datetime(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.utcoffset() is None:
            return value.replace(tzinfo=UTC)
        return value


class ProgressEventReceipt(BaseModel):
    event: ProgressEventRead
    duplicate: bool
