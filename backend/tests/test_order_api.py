from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.main import create_app
from app.models.production_order import ProductionOrder, ProductionOrderItem
from app.repositories.order_repository import OrderRepository
from app.schemas.order_schema import OrderCreate


def assert_no_orders(client: TestClient) -> None:
    assert client.get("/orders").json() == []
    with client.app.state.session_factory() as session:
        assert session.scalar(select(func.count()).select_from(ProductionOrder)) == 0
        assert session.scalar(select(func.count()).select_from(ProductionOrderItem)) == 0


def test_orders_and_restart(
    client: TestClient, products: list[dict[str, object]], empty_database: Path
) -> None:
    assert_no_orders(client)
    data = {"items": [{"product_id": p["id"], "quantity": i} for i, p in enumerate(products, 1)]}
    response = client.post("/orders", json={"items": list(reversed(data["items"]))})
    assert response.status_code == 201
    first = response.json()
    assert first == {"id": first["id"], **data}
    assert first["id"] > 0
    response = client.post("/orders", json=data)
    assert response.status_code == 201
    second = response.json()
    assert second["id"] > first["id"]
    assert second["items"] == first["items"]
    response = client.post("/orders", json={"items": data["items"][:1]})
    assert response.status_code == 201
    third = response.json()
    assert third["items"] == data["items"][:1]
    assert client.get("/orders").json() == [first, second, third]
    for order in [first, second, third]:
        response = client.get(f"/orders/{order['id']}")
        assert response.status_code == 200
        assert response.json() == order
    assert client.get("/products").json() == products
    with TestClient(create_app()) as restarted:
        assert restarted.get("/orders").json() == [first, second, third]


@pytest.mark.parametrize("field", ["product_id", "quantity"])
@pytest.mark.parametrize("value", [0, -1, None, True, False, "1", 1.0, 1.5, [], {}])
def test_strict_integers(client: TestClient, field: str, value: object) -> None:
    item = {"product_id": 1, "quantity": 1, field: value}
    response = client.post("/orders", json={"items": [item]})
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "items", 0, field]
    assert_no_orders(client)


@pytest.mark.parametrize(
    "payload",
    [
        None,
        {},
        [],
        "order",
        {"items": None},
        {"items": []},
        {"items": {}},
        {"items": "x"},
        {"items": [None]},
        {"items": [1]},
        {"items": [[]]},
        {"items": [{}]},
        {"items": [{"product_id": 1}]},
        {"items": [{"quantity": 1}]},
    ],
)
def test_invalid_structure(client: TestClient, payload: object) -> None:
    response = client.post("/orders", json=payload)
    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)
    assert_no_orders(client)


def test_absent_body(client: TestClient) -> None:
    assert client.post("/orders").status_code == 422
    assert_no_orders(client)


@pytest.mark.parametrize("field", ["id", "order_id", "unit_id", "status", "unknown"])
@pytest.mark.parametrize("target", ["order", "item"])
def test_extra_fields(client: TestClient, field: str, target: str) -> None:
    data = {"items": [{"product_id": 1, "quantity": 1}]}
    (data if target == "order" else data["items"][0])[field] = 1
    assert client.post("/orders", json=data).status_code == 422
    assert_no_orders(client)


def test_validation_order(client: TestClient, products: list[dict[str, object]]) -> None:
    for product_id in [products[0]["id"], 999]:
        data = {"items": [{"product_id": product_id, "quantity": 1}] * 2}
        response = client.post("/orders", json=data)
        assert response.status_code == 422
        assert response.json() == {"detail": "Cada produto pode aparecer somente uma vez na ordem."}
        data["items"][0] = {"product_id": product_id, "quantity": True}
        response = client.post("/orders", json=data)
        assert response.status_code == 422
        assert isinstance(response.json()["detail"], list)
    assert_no_orders(client)


def test_missing_products(client: TestClient, products: list[dict[str, object]]) -> None:
    response = client.post(
        "/orders",
        json={
            "items": [
                {"product_id": pid, "quantity": 1} for pid in [12, products[0]["id"], 9, 2**80]
            ]
        },
    )
    assert response.status_code == 422
    assert response.json() == {
        "detail": "Um ou mais produtos da ordem não existem.",
        "product_ids": [9, 12, 2**80],
    }
    assert_no_orders(client)
    assert client.get("/products").json() == products


@pytest.mark.parametrize("order_id", ["0", "-1", "abc", "1.5"])
def test_invalid_id(client: TestClient, order_id: str) -> None:
    assert client.get(f"/orders/{order_id}").status_code == 422


@pytest.mark.parametrize("order_id", [1, 2**80])
def test_not_found(client: TestClient, order_id: int) -> None:
    response = client.get(f"/orders/{order_id}")
    assert response.status_code == 404
    assert response.json() == {"detail": "Ordem de produção não encontrada."}


@pytest.mark.parametrize("failure_point", ["partial", "commit", "list", "get"])
def test_persistence_failures(
    client: TestClient,
    products: list[dict[str, object]],
    monkeypatch: pytest.MonkeyPatch,
    failure_point: str,
) -> None:
    def fail(*args: object, **kwargs: object) -> None:
        raise OperationalError("SQL secreto", {}, Exception("caminho interno"))

    def partial(repository: OrderRepository, data: OrderCreate) -> None:
        order = ProductionOrder()
        repository.session.add(order)
        repository.session.flush()
        repository.session.add(ProductionOrderItem(order_id=order.id, **data.items[0].model_dump()))
        repository.session.flush()
        fail()

    data = {"items": [{"product_id": p["id"], "quantity": 2} for p in products]}
    with monkeypatch.context() as patch:
        if failure_point == "partial":
            patch.setattr(OrderRepository, "add", partial)
        elif failure_point == "commit":
            patch.setattr(Session, "commit", fail)
        else:
            patch.setattr(OrderRepository, "list_all" if failure_point == "list" else "get", fail)
        response = (
            client.get("/orders" if failure_point == "list" else "/orders/1")
            if failure_point in {"list", "get"}
            else client.post("/orders", json=data)
        )
    assert response.status_code == 500
    assert response.json() == {"detail": "Erro interno do servidor."}
    assert_no_orders(client)
    assert client.get("/products").json() == products
    assert client.post("/orders", json=data).status_code == 201


def test_openapi(client: TestClient) -> None:
    document = client.get("/openapi.json").json()
    paths = document["paths"]
    assert set(paths["/orders"]) == {"post", "get"}
    assert set(paths["/orders/{order_id}"]) == {"get"}
    assert set(paths["/orders/{order_id}/progress"]) == {"post"}
    assert {"201", "422"} <= set(paths["/orders"]["post"]["responses"])
    assert {"200", "404", "422"} <= set(paths["/orders/{order_id}"]["get"]["responses"])
    schemas = document["components"]["schemas"]
    assert schemas["OrderCreate"]["required"] == ["items"]
    assert schemas["OrderCreate"]["properties"]["items"]["minItems"] == 1
    assert schemas["OrderItemCreate"]["required"] == ["product_id", "quantity"]
    for name in ["OrderCreate", "OrderItemCreate"]:
        assert schemas[name]["additionalProperties"] is False
    assert set(schemas["OrderRead"]["properties"]) == {"id", "items"}
    assert set(schemas["OrderItemRead"]["properties"]) == {"product_id", "quantity"}
