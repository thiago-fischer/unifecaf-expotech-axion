from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import URL, func, select
from sqlalchemy.orm import sessionmaker

from app.config import Settings
from app.database.database import build_engine
from app.main import create_app
from app.models.network import NetworkCaptureBatch, NetworkMetricSample
from app.services.network_service import NetworkEventBuffer


def event(sequence: int, *, status: int = 200, latency: float = 12.5) -> dict[str, object]:
    return {
        "sequence": sequence,
        "observed_at": "2026-11-14T15:00:05-03:00",
        "source_service": "frontend",
        "destination_service": "backend",
        "source_port": 51000,
        "destination_port": 8000,
        "protocol": "HTTP",
        "tcp_stream": 7,
        "frame_length": 400,
        "http_method": "GET",
        "http_path": "/orders/{id}",
        "status_code": status,
        "latency_ms": latency,
        "retransmission": False,
        "reset": False,
    }


def batch(batch_id: str, session_id: str, events: list[dict[str, object]]) -> dict[str, object]:
    return {
        "batch_id": batch_id,
        "capture_session_id": session_id,
        "first_sequence": events[0]["sequence"],
        "last_sequence": events[-1]["sequence"],
        "captured_at": datetime.now(UTC).isoformat(),
        "events": events,
    }


def test_capture_requires_token_and_deduplicates_batch(
    empty_database: URL, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AXION_CAPTURE_TOKEN", "capture-test")
    capture_session = str(uuid4())
    batch_id = str(uuid4())
    payload = batch(batch_id, capture_session, [event(1), event(2, status=503, latency=20)])
    with TestClient(create_app()) as client:
        assert client.post("/network/capture/events", json={}).status_code == 403
        assert client.post("/network/capture/events", json=payload).status_code == 403
        headers = {"X-Axion-Capture-Token": "capture-test"}
        assert (
            client.post("/network/capture/events", json=payload, headers=headers).status_code == 204
        )
        assert (
            client.post("/network/capture/events", json=payload, headers=headers).status_code == 204
        )
        assert client.app.state.network_event_buffer.counters() == (2, 2)
        response = client.get("/network/events?after=0&limit=1").json()
        assert response["capture_session_id"] == capture_session
        assert [item["sequence"] for item in response["events"]] == [1]
        assert response["next_sequence"] == 1

    engine = build_engine(Settings())
    try:
        with sessionmaker(engine)() as session:
            assert session.scalar(select(func.count()).select_from(NetworkCaptureBatch)) == 1
            samples = list(session.scalars(select(NetworkMetricSample)))
            assert len(samples) == 2
            assert sum(sample.request_count for sample in samples) == 2
            assert sum(sample.error_count for sample in samples) == 1
            assert sum(sample.latency_sum_ms for sample in samples) == 32.5
    finally:
        engine.dispose()


def test_capture_schema_rejects_queries_and_invalid_sequences(
    empty_database: URL, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AXION_CAPTURE_TOKEN", "capture-test")
    payload = batch(str(uuid4()), str(uuid4()), [event(2), event(1)])
    payload["events"][0]["http_path"] = "/orders/1?secret=value"
    with TestClient(create_app()) as client:
        response = client.post(
            "/network/capture/events",
            json=payload,
            headers={"X-Axion-Capture-Token": "capture-test"},
        )
        assert response.status_code == 422


def test_buffer_reports_rotation_and_session_change() -> None:
    from app.schemas.network_schema import CaptureBatch

    buffer = NetworkEventBuffer(10)
    first_session = str(uuid4())
    parsed = CaptureBatch.model_validate(
        batch(str(uuid4()), first_session, [event(sequence) for sequence in range(1, 13)])
    )
    buffer.publish(parsed)
    rotated = buffer.events(1, 100, parsed.capture_session_id)
    assert rotated.history_lost is True
    assert rotated.events[0].sequence == 3

    second = CaptureBatch.model_validate(batch(str(uuid4()), str(uuid4()), [event(1)]))
    buffer.publish(second)
    changed = buffer.events(11, 100, parsed.capture_session_id)
    assert changed.session_changed is True
    assert [item.sequence for item in changed.events] == [1]


def test_ingestion_removes_only_expired_batches_and_metrics(
    empty_database: URL, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AXION_CAPTURE_TOKEN", "capture-test")
    monkeypatch.setenv("AXION_NETWORK_BATCH_RETENTION_HOURS", "1")
    monkeypatch.setenv("AXION_NETWORK_METRICS_RETENTION_HOURS", "1")
    now = datetime.now(UTC)
    old_batch_id = str(uuid4())
    engine = build_engine(Settings())
    try:
        with sessionmaker(engine)() as session:
            session.add(
                NetworkCaptureBatch(
                    id=old_batch_id,
                    capture_session_id=str(uuid4()),
                    first_sequence=1,
                    last_sequence=1,
                    received_at=now - timedelta(hours=2),
                )
            )
            session.add(
                NetworkMetricSample(
                    bucket_start=now - timedelta(hours=2),
                    source_service="frontend",
                    destination_service="backend",
                    protocol="HTTP",
                    status_class="2xx",
                    request_count=1,
                    error_count=0,
                    bytes_total=10,
                    retransmission_count=0,
                    latency_sum_ms=1,
                    latency_count=1,
                )
            )
            session.commit()

        fresh_event = event(1)
        fresh_event["observed_at"] = now.isoformat()
        fresh_batch_id = str(uuid4())
        payload = batch(fresh_batch_id, str(uuid4()), [fresh_event])
        with TestClient(create_app()) as client:
            response = client.post(
                "/network/capture/events",
                json=payload,
                headers={"X-Axion-Capture-Token": "capture-test"},
            )
            assert response.status_code == 204

        with sessionmaker(engine)() as session:
            assert session.get(NetworkCaptureBatch, old_batch_id) is None
            assert session.get(NetworkCaptureBatch, fresh_batch_id) is not None
            samples = list(session.scalars(select(NetworkMetricSample)))
            assert len(samples) == 1
            assert samples[0].bucket_start > now - timedelta(hours=1)
    finally:
        engine.dispose()


@pytest.mark.parametrize(
    ("name", "value", "message"),
    [
        ("AXION_GRAFANA_PUBLIC_URL", "javascript:alert(1)", "URL HTTP válida"),
        ("AXION_GRAFANA_PUBLIC_URL", "http://user:secret@localhost:3000", "credenciais"),
        ("AXION_GRAFANA_PUBLIC_URL", "http://grafana.example:3000", "host local"),
    ],
)
def test_grafana_public_url_is_safe(
    monkeypatch: pytest.MonkeyPatch, name: str, value: str, message: str
) -> None:
    monkeypatch.setenv(name, value)
    with pytest.raises(RuntimeError, match=message):
        Settings()
