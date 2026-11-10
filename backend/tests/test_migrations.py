import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import URL, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import Settings
from app.database.database import build_engine
from app.main import create_app
from app.models.product import Product
from app.models.product_step import ProductStep


def test_upgrade_repeat_downgrade_and_upgrade(alembic_config: Config) -> None:
    command.upgrade(alembic_config, "d8e063d489f1")
    with TestClient(create_app()) as client:
        assert client.get("/machines").json() == []
        machine = client.post("/machines", json={"name": "Migration"}).json()
    command.upgrade(alembic_config, "d8e063d489f1")
    with TestClient(create_app()) as client:
        assert client.get("/machines").json() == [machine]
    command.downgrade(alembic_config, "base")
    engine = build_engine(Settings())
    try:
        assert "machines" not in inspect(engine).get_table_names()
    finally:
        engine.dispose()
    command.upgrade(alembic_config, "d8e063d489f1")
    with TestClient(create_app()) as client:
        assert client.get("/machines").json() == []
        assert client.post("/machines", json={"name": "Nova"}).status_code == 201


def test_overridden_url_is_shared(
    alembic_config: Config,
    database_url: URL,
) -> None:
    command.upgrade(alembic_config, "head")
    assert Settings().database_url == database_url
    with TestClient(create_app()) as client:
        assert client.post("/machines", json={"name": "Mesmo banco"}).status_code == 201
    command.check(alembic_config)


@pytest.mark.parametrize(
    "value,message",
    [
        (None, "Defina AXION_DATABASE_URL"),
        ("not a url", "URL inválida"),
        ("sqlite+pysqlite:///data/axion.db", "postgresql\\+psycopg"),
        ("postgresql+psycopg:///axion", "host e nome do banco"),
    ],
)
def test_database_url_validation(
    monkeypatch: pytest.MonkeyPatch, value: str | None, message: str
) -> None:
    if value is None:
        monkeypatch.delenv("AXION_DATABASE_URL")
    else:
        monkeypatch.setenv("AXION_DATABASE_URL", value)
    with pytest.raises(RuntimeError, match=message):
        Settings()


def test_products_upgrade_existing_database_and_downgrade(alembic_config: Config) -> None:
    command.upgrade(alembic_config, "77be86445d30")
    with TestClient(create_app()) as client:
        machine = client.post("/machines", json={"name": "Preservada"}).json()
    command.upgrade(alembic_config, "d8e063d489f1")
    with TestClient(create_app()) as client:
        product = client.post(
            "/products",
            json={
                "name": "P",
                "steps": [
                    {"sequence": 1, "machine_id": machine["id"], "processing_time_seconds": 10}
                ],
            },
        ).json()
        assert product["id"] > 0
    command.upgrade(alembic_config, "d8e063d489f1")
    with TestClient(create_app()) as client:
        assert client.get("/machines").json() == [machine]
        assert client.get("/products").json() == [product]
    command.downgrade(alembic_config, "77be86445d30")
    engine = build_engine(Settings())
    try:
        assert set(inspect(engine).get_table_names()) == {"machines", "alembic_version"}
    finally:
        engine.dispose()
    command.upgrade(alembic_config, "d8e063d489f1")
    with TestClient(create_app()) as client:
        assert client.get("/machines").json() == [machine]
        assert client.get("/products").json() == []


@pytest.mark.parametrize(
    "changes",
    [
        {"product_id": 999},
        {"machine_id": 999},
        {"sequence": 0},
        {"sequence": -1},
        {"processing_time_seconds": 0},
        {"processing_time_seconds": -1},
        {},
    ],
)
def test_product_step_database_constraints(session: Session, changes: dict[str, int]) -> None:
    from app.services.machine_service import MachineService

    machine = MachineService(session).create("M")
    product = Product(name="P")
    session.add(product)
    session.flush()
    values = {
        "product_id": product.id,
        "sequence": 1,
        "machine_id": machine.id,
        "processing_time_seconds": 10,
    }
    session.add(ProductStep(**values))
    session.commit()
    # Direct SQL bypasses both service validation and ORM identity handling.
    with pytest.raises(IntegrityError):
        session.execute(
            text(
                "INSERT INTO product_steps VALUES "
                "(:product_id, :sequence, :machine_id, :processing_time_seconds)"
            ),
            {**values, **changes},
        )
    session.rollback()
    for table, identifier in [("machines", machine.id), ("products", product.id)]:
        with pytest.raises(IntegrityError):
            session.execute(text(f"DELETE FROM {table} WHERE id = :id"), {"id": identifier})
        session.rollback()


def test_foreign_keys_on_each_connection(migrated_database: URL) -> None:
    engine = build_engine(Settings())
    try:
        for _ in range(2):
            with engine.connect() as connection, pytest.raises(IntegrityError):
                connection.execute(
                    text(
                        "INSERT INTO product_steps "
                        "(product_id, sequence, machine_id, processing_time_seconds) "
                        "VALUES (999999, 1, 999999, 1)"
                    )
                )
    finally:
        engine.dispose()


def test_orders_upgrade_preserves_catalog_and_downgrade(alembic_config: Config) -> None:
    command.upgrade(alembic_config, "bb94b7e72eb7")
    with TestClient(create_app()) as client:
        machines = client.get("/machines").json()
        products = client.get("/products").json()
    command.upgrade(alembic_config, "head")
    command.check(alembic_config)
    with TestClient(create_app()) as client:
        assert client.get("/machines").json() == machines
        assert client.get("/products").json() == products
        assert client.get("/orders").json() == []
        order = client.post(
            "/orders", json={"items": [{"product_id": products[0]["id"], "quantity": 3}]}
        ).json()
        assert order["id"] > 0
    command.upgrade(alembic_config, "head")
    with TestClient(create_app()) as client:
        assert client.get("/orders").json() == [order]
    command.downgrade(alembic_config, "bb94b7e72eb7")
    engine = build_engine(Settings())
    try:
        assert set(inspect(engine).get_table_names()) == {
            "machines",
            "products",
            "product_steps",
            "alembic_version",
        }
    finally:
        engine.dispose()
    with TestClient(create_app()) as client:
        assert client.get("/machines").json() == machines
        assert client.get("/products").json() == products
    command.upgrade(alembic_config, "head")
    with TestClient(create_app()) as client:
        assert client.get("/orders").json() == []
        assert client.get("/products").json() == products
    command.check(alembic_config)
    command.downgrade(alembic_config, "base")
    command.upgrade(alembic_config, "head")
    command.check(alembic_config)


@pytest.mark.parametrize(
    "changes",
    [
        {},
        {"order_id": 999},
        {"product_id": 999},
        {"quantity": 0},
        {"quantity": -1},
        {"quantity": None},
        {"order_id": None},
        {"product_id": None},
    ],
)
def test_order_item_database_constraints(session: Session, changes: dict[str, int | None]) -> None:
    from app.models.production_order import ProductionOrder, ProductionOrderItem

    product = Product(name="P")
    order = ProductionOrder()
    session.add_all([product, order])
    session.flush()
    values = {"order_id": order.id, "product_id": product.id, "quantity": 2}
    session.add(ProductionOrderItem(**values))
    # A free composite key ensures quantity checks cannot pass via duplicate-key errors.
    other_order = ProductionOrder()
    session.add(other_order)
    session.commit()
    candidate = {**values, **changes}
    if "quantity" in changes:
        candidate["order_id"] = other_order.id
    with pytest.raises(IntegrityError):
        session.execute(
            text(
                "INSERT INTO production_order_items (order_id, product_id, quantity) "
                "VALUES (:order_id, :product_id, :quantity)"
            ),
            candidate,
        )
    session.rollback()
    for table, identifier in [("products", product.id), ("production_orders", order.id)]:
        with pytest.raises(IntegrityError):
            session.execute(text(f"DELETE FROM {table} WHERE id = :id"), {"id": identifier})
        session.rollback()
