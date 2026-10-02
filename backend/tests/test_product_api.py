from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.main import create_app
from app.models.product import Product
from app.repositories.product_repository import ProductRepository


def recipe(machine_id: int = 1) -> dict[str, object]:
    return {
        "name": "  Produto  Á  ",
        "steps": [{"sequence": 1, "machine_id": machine_id, "processing_time_seconds": 10}],
    }


def test_catalog_and_restart(migrated_database: Path) -> None:
    with TestClient(create_app()) as client:
        assert client.get("/products").json() == []
        machine = client.post("/machines", json={"name": "M"}).json()
        data = recipe(machine["id"])
        data["steps"] = [
            {"sequence": 2, "machine_id": machine["id"], "processing_time_seconds": 20},
            {"sequence": 1, "machine_id": machine["id"], "processing_time_seconds": 10},
        ]
        response = client.post("/products", json=data)
        assert response.status_code == 201
        first = response.json()
        assert first["id"] > 0 and first["name"] == "Produto  Á"
        assert first["steps"] == sorted(data["steps"], key=lambda step: step["sequence"])
        second = client.post("/products", json=data).json()
        assert second["id"] > first["id"]
        assert client.get("/products").json() == [first, second]
        assert client.get(f"/products/{first['id']}").json() == first
    with TestClient(create_app()) as restarted:
        assert restarted.get("/products").json() == [first, second]


@pytest.mark.parametrize("length", [1, 100])
def test_name_boundaries(client: TestClient, length: int) -> None:
    machine = client.post("/machines", json={"name": "M"}).json()
    data = recipe(machine["id"])
    data["name"] = "  " + "Á" * length + "  "
    response = client.post("/products", json=data)
    assert response.status_code == 201
    assert response.json()["name"] == "Á" * length


@pytest.mark.parametrize("name", [None, "", " \t ", 123, True, [], {}, "x" * 101])
def test_invalid_names(client: TestClient, name: object) -> None:
    data = recipe()
    data["name"] = name
    assert client.post("/products", json=data).status_code == 422
    assert client.get("/products").json() == []


@pytest.mark.parametrize("field", ["sequence", "machine_id", "processing_time_seconds"])
@pytest.mark.parametrize("value", [0, -1, None, True, False, "1", 1.0, 1.5])
def test_strict_step_integers(client: TestClient, field: str, value: object) -> None:
    data = recipe()
    data["steps"][0][field] = value
    response = client.post("/products", json=data)
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "steps", 0, field]
    assert client.get("/products").json() == []


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"steps": []},
        {"name": "P"},
        {"name": "P", "steps": None},
        {"name": "P", "steps": []},
        {"name": "P", "steps": {}},
        {"name": "P", "steps": "x"},
        {"name": "P", "steps": [1]},
        {"name": "P", "steps": [{}]},
        [],
        "P",
    ],
)
def test_invalid_structure(client: TestClient, payload: object) -> None:
    assert client.post("/products", json=payload).status_code == 422
    assert client.get("/products").json() == []


@pytest.mark.parametrize("field", ["sequence", "machine_id", "processing_time_seconds"])
def test_missing_step_fields(client: TestClient, field: str) -> None:
    data = recipe()
    del data["steps"][0][field]
    assert client.post("/products", json=data).status_code == 422
    assert client.get("/products").json() == []


@pytest.mark.parametrize("field", ["id", "product_id", "quantity", "unit_id", "unknown"])
@pytest.mark.parametrize("target", ["product", "step"])
def test_extra_fields(client: TestClient, field: str, target: str) -> None:
    data = recipe()
    (data if target == "product" else data["steps"][0])[field] = 1
    assert client.post("/products", json=data).status_code == 422
    assert client.get("/products").json() == []


@pytest.mark.parametrize("sequences", [[2], [1, 1], [1, 3]])
def test_invalid_sequence_precedes_machine_check(client: TestClient, sequences: list[int]) -> None:
    data = recipe()
    data["steps"] = [
        {"sequence": sequence, "machine_id": 99, "processing_time_seconds": 1}
        for sequence in sequences
    ]
    response = client.post("/products", json=data)
    assert response.status_code == 422
    assert response.json() == {
        "detail": "As sequências das etapas devem ser únicas e consecutivas, de 1 a N."
    }
    assert client.get("/products").json() == []


def test_missing_machines(client: TestClient) -> None:
    machine = client.post("/machines", json={"name": "M"}).json()
    data = recipe()
    data["steps"] = [
        {"sequence": index, "machine_id": mid, "processing_time_seconds": 1}
        for index, mid in enumerate([12, machine["id"], 9, 12, 2**80], 1)
    ]
    response = client.post("/products", json=data)
    assert response.status_code == 422
    assert response.json() == {
        "detail": "Uma ou mais máquinas das etapas não existem.",
        "machine_ids": [9, 12, 2**80],
    }
    assert client.get("/products").json() == []
    assert client.get("/machines").json() == [machine]


@pytest.mark.parametrize("product_id", ["0", "-1", "abc", "1.5"])
def test_invalid_id(client: TestClient, product_id: str) -> None:
    assert client.get(f"/products/{product_id}").status_code == 422


@pytest.mark.parametrize("product_id", [1, 2**80])
def test_not_found(client: TestClient, product_id: int) -> None:
    response = client.get(f"/products/{product_id}")
    assert response.status_code == 404
    assert response.json() == {"detail": "Produto não encontrado."}


@pytest.mark.parametrize("failure_point", ["partial", "commit", "read"])
def test_persistence_failures(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, failure_point: str
) -> None:
    machine = client.post("/machines", json={"name": "M"}).json()

    def fail(*args: object, **kwargs: object) -> None:
        raise OperationalError("SQL secreto", {}, Exception("simulada"))

    def partial(repository: ProductRepository, data: object) -> None:
        repository.session.add(Product(name="Parcial"))
        repository.session.flush()
        fail()

    with monkeypatch.context() as patch:
        if failure_point == "partial":
            patch.setattr(ProductRepository, "add", partial)
        elif failure_point == "commit":
            patch.setattr(Session, "commit", fail)
        else:
            patch.setattr(ProductRepository, "list_all", fail)
        response = (
            client.get("/products")
            if failure_point == "read"
            else client.post("/products", json=recipe(machine["id"]))
        )
    assert response.status_code == 500
    assert response.json() == {"detail": "Erro interno do servidor."}
    assert client.get("/products").json() == []
    assert client.get("/machines").json() == [machine]
    assert client.post("/products", json=recipe(machine["id"])).status_code == 201


def test_openapi(client: TestClient) -> None:
    document = client.get("/openapi.json").json()
    assert set(document["paths"]) == {
        "/machines",
        "/machines/{machine_id}",
        "/products",
        "/products/{product_id}",
    }
    assert {"201", "422"} <= set(document["paths"]["/products"]["post"]["responses"])
    assert {"200", "404", "422"} <= set(
        document["paths"]["/products/{product_id}"]["get"]["responses"]
    )
    schemas = document["components"]["schemas"]
    assert schemas["ProductCreate"]["required"] == ["name", "steps"]
    assert schemas["ProductCreate"]["additionalProperties"] is False
    assert schemas["ProductStepCreate"]["additionalProperties"] is False
