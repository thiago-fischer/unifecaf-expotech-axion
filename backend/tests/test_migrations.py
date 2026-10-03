from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import BACKEND_DIR, Settings
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


def test_overridden_path_is_shared(
    alembic_config: Config,
    database_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    command.upgrade(alembic_config, "head")
    assert Settings().database_path == database_path
    assert database_path.exists()
    with TestClient(create_app()) as client:
        assert client.post("/machines", json={"name": "Mesmo banco"}).status_code == 201
    command.check(alembic_config)


def test_default_and_relative_paths_are_module_relative(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("AXION_DATABASE_PATH", raising=False)
    assert Settings().database_path == BACKEND_DIR / "data" / "axion.db"
    monkeypatch.setenv("AXION_DATABASE_PATH", "custom/machines.db")
    assert Settings().database_path == BACKEND_DIR / "custom" / "machines.db"


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
    assert session.scalar(text("PRAGMA foreign_keys")) == 1
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


def test_foreign_keys_on_each_connection(migrated_database: Path) -> None:
    engine = build_engine(Settings())
    try:
        with engine.connect() as first, engine.connect() as second:
            assert first.scalar(text("PRAGMA foreign_keys")) == 1
            assert second.scalar(text("PRAGMA foreign_keys")) == 1
    finally:
        engine.dispose()
