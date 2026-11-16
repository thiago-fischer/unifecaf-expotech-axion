from __future__ import annotations

from collections import deque
from datetime import UTC, datetime, timedelta
from threading import Lock
from time import monotonic
from uuid import UUID

from sqlalchemy.orm import Session

from app.config import Settings
from app.repositories.network_repository import NetworkRepository
from app.schemas.network_schema import (
    BufferedNetworkEvent,
    CaptureBatch,
    NetworkEvent,
    NetworkEventsResponse,
)


class NetworkEventBuffer:
    def __init__(self, maximum: int) -> None:
        self._events: deque[BufferedNetworkEvent] = deque(maxlen=maximum)
        self._lock = Lock()
        self._session: UUID | None = None
        self._last_batch_at: float | None = None
        self._accepted_batches = 0
        self._blocked_batches = 0

    def publish(self, batch: CaptureBatch) -> None:
        with self._lock:
            if self._session != batch.capture_session_id:
                self._events.clear()
                self._session = batch.capture_session_id
            self._events.extend(
                BufferedNetworkEvent(
                    **event.model_dump(), capture_session_id=batch.capture_session_id
                )
                for event in batch.events
            )
            self._last_batch_at = monotonic()

    def heartbeat(self, capture_session_id: UUID) -> None:
        with self._lock:
            if self._session != capture_session_id:
                self._events.clear()
                self._session = capture_session_id
            self._last_batch_at = monotonic()

    def accepted_batch(self) -> None:
        with self._lock:
            self._accepted_batches += 1

    def blocked_batch(self) -> None:
        with self._lock:
            self._blocked_batches += 1

    def counters(self) -> tuple[int, int]:
        with self._lock:
            return self._accepted_batches, self._blocked_batches

    def events(
        self, after: int, limit: int, capture_session_id: UUID | None
    ) -> NetworkEventsResponse:
        with self._lock:
            current = self._session
            session_changed = capture_session_id is not None and capture_session_id != current
            effective_after = 0 if session_changed else after
            first = self._events[0].sequence if self._events else effective_after + 1
            history_lost = bool(
                current is not None
                and not session_changed
                and effective_after > 0
                and effective_after < first - 1
            )
            selected = [event for event in self._events if event.sequence > effective_after][:limit]
            next_sequence = selected[-1].sequence if selected else effective_after
            age = (
                max(0.0, (monotonic() - self._last_batch_at) * 1000)
                if self._last_batch_at is not None
                else None
            )
            return NetworkEventsResponse(
                capture_session_id=current,
                events=[event.model_copy(deep=True) for event in selected],
                next_sequence=next_sequence,
                history_lost=history_lost,
                session_changed=session_changed,
                last_batch_age_ms=age,
            )

    def snapshot(self) -> tuple[UUID | None, datetime | None, float | None, set[tuple[str, str]]]:
        with self._lock:
            last_event = self._events[-1].observed_at if self._events else None
            age = (
                max(0.0, (monotonic() - self._last_batch_at) * 1000)
                if self._last_batch_at is not None
                else None
            )
            connections = {
                (event.source_service, event.destination_service) for event in self._events
            }
            return self._session, last_event, age, connections


class NetworkIngestionService:
    def __init__(
        self,
        session: Session,
        buffer: NetworkEventBuffer,
        settings: Settings,
    ) -> None:
        self.session = session
        self.buffer = buffer
        self.settings = settings

    def ingest(self, batch: CaptureBatch) -> bool:
        repository = NetworkRepository(self.session)
        received_at = datetime.now(UTC)
        with self.session.begin():
            added = repository.add_batch(
                str(batch.batch_id),
                str(batch.capture_session_id),
                batch.first_sequence,
                batch.last_sequence,
                received_at,
            )
            if not added:
                return False
            repository.add_metrics(self._aggregate(batch.events))
            repository.delete_expired(
                received_at - timedelta(hours=self.settings.network_batch_retention_hours),
                received_at - timedelta(hours=self.settings.network_metrics_retention_hours),
            )
        self.buffer.publish(batch)
        return True

    def _aggregate(self, events: list[NetworkEvent]) -> list[dict[str, object]]:
        buckets: dict[tuple[object, ...], dict[str, object]] = {}
        interval = self.settings.network_bucket_seconds
        for event in events:
            timestamp = int(event.observed_at.timestamp())
            bucket_start = datetime.fromtimestamp(timestamp - timestamp % interval, UTC)
            status_class = f"{event.status_code // 100}xx" if event.status_code else None
            key = (
                bucket_start,
                event.source_service,
                event.destination_service,
                event.protocol,
                status_class,
            )
            values = buckets.setdefault(
                key,
                {
                    "bucket_start": bucket_start,
                    "source_service": event.source_service,
                    "destination_service": event.destination_service,
                    "protocol": event.protocol,
                    "status_class": status_class,
                    "request_count": 0,
                    "error_count": 0,
                    "bytes_total": 0,
                    "retransmission_count": 0,
                    "latency_sum_ms": 0.0,
                    "latency_count": 0,
                },
            )
            values["request_count"] = int(values["request_count"]) + bool(event.http_method)
            values["error_count"] = int(values["error_count"]) + bool(
                event.status_code and event.status_code >= 400
            )
            values["bytes_total"] = int(values["bytes_total"]) + event.frame_length
            values["retransmission_count"] = int(values["retransmission_count"]) + int(
                event.retransmission
            )
            if event.latency_ms is not None:
                values["latency_sum_ms"] = float(values["latency_sum_ms"]) + event.latency_ms
                values["latency_count"] = int(values["latency_count"]) + 1
        return list(buckets.values())
