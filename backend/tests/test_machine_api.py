import logging
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.main import create_app
from app.repositories.machine_repository import MachineRepository


def test_create_list_and_get(client: TestClient) -> None:
    assert client.get("/machines").json() == []
    response = client.post("/machines", json={"name": " \tMáquina  de Corte\n"})
    assert response.status_code == 201
    machine = response.json()
    assert isinstance(machine["id"], int) and machine["id"] > 0
    assert machine["name"] == "Máquina  de Corte"
    second = client.post("/machines", json={"name": machine["name"]}).json()
    assert second["id"] > machine["id"]
    listing = client.get("/machines")
    assert listing.status_code == 200
    assert listing.json() == [machine, second]
    found = client.get(f"/machines/{machine['id']}")
    assert found.status_code == 200
    assert found.json() == machine


@pytest.mark.parametrize("length", [1, 100])
def test_name_boundaries(client: TestClient, length: int) -> None:
    response = client.post("/machines", json={"name": "  " + "Á" * length + "  "})
    assert response.status_code == 201
    assert response.json()["name"] == "Á" * length


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"name": None},
        {"name": ""},
        {"name": " \n\t\u2003 "},
        {"name": 123},
        {"name": 1.5},
        {"name": True},
        {"name": []},
        {"name": {}},
        {"name": "x" * 101},
        {"name": "ok", "id": 1},
        {"name": "ok", "status": "idle"},
        {"name": "ok", "processing_time": 10},
        {"name": "ok", "unknown": "field"},
        [],
        "name",
    ],
)
def test_invalid_payload_does_not_persist(client: TestClient, payload: object) -> None:
    response = client.post("/machines", json=payload)
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"][0] == "body"
    assert client.get("/machines").json() == []


@pytest.mark.parametrize("machine_id", ["0", "-1", "abc", "1.5"])
def test_invalid_id(client: TestClient, machine_id: str) -> None:
    response = client.get(f"/machines/{machine_id}")
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["path", "machine_id"]


@pytest.mark.parametrize("machine_id", [12345, 2**80])
def test_missing_machine(client: TestClient, machine_id: int) -> None:
    response = client.get(f"/machines/{machine_id}")
    assert response.status_code == 404
    assert response.json() == {"detail": "Máquina não encontrada."}


def test_data_survives_application_restart(migrated_database: Path) -> None:
    with TestClient(create_app()) as first:
        machine = first.post("/machines", json={"name": "Persistente"}).json()
    with TestClient(create_app()) as restarted:
        assert restarted.get(f"/machines/{machine['id']}").json() == machine


@pytest.mark.parametrize("failure_point", ["flush", "commit", "read"])
def test_persistence_failure(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    failure_point: str,
) -> None:
    def fail(*args: object, **kwargs: object) -> None:
        raise OperationalError("SQL segredo caminho/interno", {}, Exception("erro simulado"))

    with monkeypatch.context() as patch:
        if failure_point == "read":
            patch.setattr(MachineRepository, "list_all", fail)
        else:
            patch.setattr(Session, failure_point, fail)
        with caplog.at_level(logging.ERROR):
            response = (
                client.get("/machines")
                if failure_point == "read"
                else client.post("/machines", json={"name": "Não gravar"})
            )
    assert response.status_code == 500
    assert response.json() == {"detail": "Erro interno do servidor."}
    assert "Falha de persistência" in caplog.text
    assert client.get("/machines").json() == []


def test_openapi_contract(client: TestClient) -> None:
    document = client.get("/openapi.json").json()
    assert set(document["paths"]) == {"/machines", "/machines/{machine_id}"}
    assert set(document["paths"]["/machines"]) == {"post", "get"}
    assert "201" in document["paths"]["/machines"]["post"]["responses"]
    assert "422" in document["paths"]["/machines"]["post"]["responses"]
    assert {"200", "404", "422"} <= set(
        document["paths"]["/machines/{machine_id}"]["get"]["responses"]
    )
    schema = document["components"]["schemas"]["MachineCreate"]
    assert schema["additionalProperties"] is False
    assert schema["required"] == ["name"]
    assert schema["properties"]["name"]["maxLength"] == 100


def test_startup_does_not_create_database(database_path: Path) -> None:
    with TestClient(create_app()) as client:
        assert client.get("/openapi.json").status_code == 200
    assert not database_path.exists()
