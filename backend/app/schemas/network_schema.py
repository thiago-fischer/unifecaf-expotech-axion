from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

ServiceName = Literal["frontend", "backend", "controller", "database", "grafana"]
ProtocolName = Literal["HTTP", "PostgreSQL", "TCP"]
HealthState = Literal["online", "degraded", "offline", "disabled", "unknown"]


class NetworkEvent(BaseModel):
    sequence: int = Field(gt=0)
    observed_at: datetime
    source_service: ServiceName
    destination_service: ServiceName
    source_port: int = Field(ge=1, le=65535)
    destination_port: int = Field(ge=1, le=65535)
    protocol: ProtocolName
    tcp_stream: int = Field(ge=0)
    frame_length: int = Field(ge=0, le=16_777_216)
    http_method: str | None = Field(default=None, max_length=16)
    http_path: str | None = Field(default=None, max_length=256)
    status_code: int | None = Field(default=None, ge=100, le=599)
    latency_ms: float | None = Field(default=None, ge=0, le=300_000)
    retransmission: bool = False
    reset: bool = False

    @field_validator("observed_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("observed_at deve conter fuso horário")
        return value

    @field_validator("http_path")
    @classmethod
    def safe_path(cls, value: str | None) -> str | None:
        if value is not None and (not value.startswith("/") or "?" in value or "#" in value):
            raise ValueError("http_path deve ser absoluto e não pode conter query ou fragmento")
        return value


class CaptureBatch(BaseModel):
    batch_id: UUID
    capture_session_id: UUID
    first_sequence: int = Field(gt=0)
    last_sequence: int = Field(gt=0)
    captured_at: datetime
    events: list[NetworkEvent] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_sequence(self) -> "CaptureBatch":
        sequences = [event.sequence for event in self.events]
        if sequences != sorted(set(sequences)):
            raise ValueError("events deve ter sequências únicas e crescentes")
        if sequences[0] != self.first_sequence or sequences[-1] != self.last_sequence:
            raise ValueError("first_sequence e last_sequence devem corresponder aos eventos")
        if self.captured_at.tzinfo is None or self.captured_at.utcoffset() is None:
            raise ValueError("captured_at deve conter fuso horário")
        return self


class CaptureHeartbeat(BaseModel):
    capture_session_id: UUID


class BufferedNetworkEvent(NetworkEvent):
    capture_session_id: UUID


class NetworkEventsResponse(BaseModel):
    capture_session_id: UUID | None
    events: list[BufferedNetworkEvent]
    next_sequence: int
    history_lost: bool
    session_changed: bool
    last_batch_age_ms: float | None


class ServiceHealth(BaseModel):
    state: HealthState
    detail: str | None = None


class NetworkConnection(BaseModel):
    source: ServiceName
    destination: ServiceName
    visibility: Literal["observed", "configured", "unavailable"]


class NetworkSecurity(BaseModel):
    controller_token_configured: bool
    capture_token_configured: bool
    local_http_without_tls: bool = True
    ports_restricted_to_host: bool = True
    raw_capture_storage_disabled: bool = True
    accepted_batches: int = Field(ge=0)
    blocked_batches: int = Field(ge=0)


class NetworkOverview(BaseModel):
    capture_session_id: UUID | None
    last_event_at: datetime | None
    last_batch_age_ms: float | None
    services: dict[str, ServiceHealth]
    connections: list[NetworkConnection]
    security: NetworkSecurity
    grafana_public_url: str
    grafana_dashboard_uid: str
