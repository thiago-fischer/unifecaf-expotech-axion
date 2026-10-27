from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.models.progress_event import ProgressEvent


def create_order(client: TestClient, product_id: int) -> int:
    response = client.post(
        "/orders",
        json={"items": [{"product_id": product_id, "quantity": 1}]},
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_progress_event_is_persisted_and_idempotent(
    client: TestClient, products: list[dict[str, object]]
) -> None:
    order_id = create_order(client, products[0]["id"])
    payload = {
        "device_id": "esp32-linha-01",
        "event_id": "evt-001",
        "unit_id": "MAT-001",
        "product_id": products[0]["id"],
        "status": "in_progress",
        "step_sequence": 1,
        "occurred_at": "2026-10-26T19:00:00-03:00",
    }

    response = client.post(f"/orders/{order_id}/progress", json=payload)

    assert response.status_code == 201
    first = response.json()
    assert first["duplicate"] is False
    assert first["event"]["received_at"].endswith("Z")
    assert first["event"]["occurred_at"] == "2026-10-26T22:00:00Z"

    response = client.post(f"/orders/{order_id}/progress", json=payload)
    assert response.status_code == 200
    assert response.json() == {**first, "duplicate": True}

    with client.app.state.session_factory() as session:
        assert session.scalar(select(func.count()).select_from(ProgressEvent)) == 1


def test_progress_event_id_cannot_be_reused_with_different_payload(
    client: TestClient, products: list[dict[str, object]]
) -> None:
    order_id = create_order(client, products[0]["id"])
    payload = {
        "device_id": "esp32-linha-01",
        "event_id": "evt-001",
        "unit_id": "MAT-001",
        "product_id": products[0]["id"],
        "status": "started",
    }
    assert client.post(f"/orders/{order_id}/progress", json=payload).status_code == 201

    response = client.post(
        f"/orders/{order_id}/progress",
        json={**payload, "status": "completed"},
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "O identificador do evento já foi utilizado com outro conteúdo."
    }


def test_progress_event_requires_existing_order_and_product_membership(
    client: TestClient, products: list[dict[str, object]]
) -> None:
    order_id = create_order(client, products[0]["id"])
    payload = {
        "device_id": "esp32-linha-01",
        "event_id": "evt-001",
        "unit_id": "MAT-001",
        "product_id": products[0]["id"],
        "status": "started",
    }

    missing_order = client.post("/orders/999/progress", json=payload)
    assert missing_order.status_code == 404

    wrong_product = client.post(
        f"/orders/{order_id}/progress",
        json={**payload, "product_id": products[1]["id"]},
    )
    assert wrong_product.status_code == 422
    assert wrong_product.json() == {"detail": "O produto informado não pertence à ordem."}

    with client.app.state.session_factory() as session:
        assert session.scalar(select(func.count()).select_from(ProgressEvent)) == 0


def test_progress_event_rejects_invalid_values_without_persisting(
    client: TestClient, products: list[dict[str, object]]
) -> None:
    order_id = create_order(client, products[0]["id"])
    valid_payload = {
        "device_id": "esp32-linha-01",
        "event_id": "evt-001",
        "unit_id": "MAT-001",
        "product_id": products[0]["id"],
        "status": "started",
    }
    invalid_payloads = [
        {**valid_payload, "status": "unknown"},
        {**valid_payload, "product_id": True},
        {**valid_payload, "device_id": "invalid device id"},
        {**valid_payload, "extra": "forbidden"},
        {**valid_payload, "occurred_at": "2026-10-26T19:00:00"},
    ]

    for payload in invalid_payloads:
        response = client.post(f"/orders/{order_id}/progress", json=payload)
        assert response.status_code == 422

    with client.app.state.session_factory() as session:
        assert session.scalar(select(func.count()).select_from(ProgressEvent)) == 0


def test_progress_event_survives_database_session(
    client: TestClient, products: list[dict[str, object]]
) -> None:
    order_id = create_order(client, products[0]["id"])
    response = client.post(
        f"/orders/{order_id}/progress",
        json={
            "device_id": "esp32-linha-01",
            "event_id": "evt-001",
            "unit_id": "MAT-001",
            "product_id": products[0]["id"],
            "status": "completed",
        },
    )
    event_id = response.json()["event"]["id"]

    with client.app.state.session_factory() as session:
        event = session.get(ProgressEvent, event_id)
        assert event is not None
        assert event.status == "completed"
        assert event.order_id == order_id


def test_progress_contract_is_in_openapi(client: TestClient) -> None:
    document = client.get("/openapi.json").json()
    operation = document["paths"]["/orders/{order_id}/progress"]["post"]

    assert {"200", "201", "404", "409", "422"} <= set(operation["responses"])
    schema = document["components"]["schemas"]["ProgressEventCreate"]
    assert schema["required"] == [
        "device_id",
        "event_id",
        "unit_id",
        "product_id",
        "status",
    ]
    assert schema["additionalProperties"] is False
    status_schema = schema["properties"]["status"]
    if "$ref" in status_schema:
        status_name = status_schema["$ref"].rsplit("/", 1)[-1]
        status_schema = document["components"]["schemas"][status_name]
    assert status_schema["enum"] == [
        "started",
        "in_progress",
        "completed",
        "failed",
    ]
