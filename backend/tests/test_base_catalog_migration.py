from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import inspect

from app.config import Settings
from app.database.database import build_engine
from app.main import create_app


def assert_base_catalog(client: TestClient) -> None:
    machines = {machine["name"]: machine["id"] for machine in client.get("/machines").json()}
    assert {"Torno CNC", "Fresadora CNC", "Centro de Usinagem CNC"} <= machines.keys()
    expected = {
        "Eixo escalonado": [("Torno CNC", 10), ("Centro de Usinagem CNC", 15)],
        "Placa de fixação": [("Fresadora CNC", 15), ("Centro de Usinagem CNC", 20)],
        "Suporte usinado": [
            ("Torno CNC", 10),
            ("Fresadora CNC", 15),
            ("Centro de Usinagem CNC", 20),
        ],
    }
    for name, recipe in expected.items():
        steps = [
            {"sequence": sequence, "machine_id": machines[machine], "processing_time_seconds": time}
            for sequence, (machine, time) in enumerate(recipe, 1)
        ]
        assert any(
            product["name"] == name and product["steps"] == steps
            for product in client.get("/products").json()
        )


def test_base_catalog_repeat_downgrade_and_reapply(alembic_config: Config) -> None:
    command.upgrade(alembic_config, "head")
    command.check(alembic_config)
    with TestClient(create_app()) as client:
        assert_base_catalog(client)
        machines = client.get("/machines").json()
        products = client.get("/products").json()
        assert len(machines) == len(products) == 3
        assert all(machine["id"] > 0 for machine in machines)
        assert all(product["id"] > 0 for product in products)
        custom = client.post(
            "/products",
            json={
                "name": "Peça personalizada",
                "steps": [
                    {"sequence": 1, "machine_id": machines[0]["id"], "processing_time_seconds": 30}
                ],
            },
        ).json()
    command.upgrade(alembic_config, "head")
    command.downgrade(alembic_config, "d8e063d489f1")
    with TestClient(create_app()) as client:
        assert client.get("/machines").json() == machines
        assert client.get("/products").json() == [*products, custom]
    command.upgrade(alembic_config, "head")
    with TestClient(create_app()) as client:
        assert client.get("/machines").json() == machines
        assert client.get("/products").json() == [*products, custom]
    command.downgrade(alembic_config, "base")
    engine = build_engine(Settings())
    try:
        assert set(inspect(engine).get_table_names()) == {"alembic_version"}
    finally:
        engine.dispose()
    command.upgrade(alembic_config, "head")
    with TestClient(create_app()) as client:
        assert_base_catalog(client)
        assert len(client.get("/machines").json()) == 3
        assert len(client.get("/products").json()) == 3


def test_base_catalog_preserves_existing_records_and_reuses_matches(alembic_config: Config) -> None:
    command.upgrade(alembic_config, "d8e063d489f1")
    with TestClient(create_app()) as client:
        custom_machine = client.post("/machines", json={"name": "Máquina existente"}).json()
        lathe = client.post("/machines", json={"name": "Torno CNC"}).json()
        duplicate = client.post("/machines", json={"name": "Torno CNC"}).json()
        center = client.post("/machines", json={"name": "Centro de Usinagem CNC"}).json()
        custom_product = client.post(
            "/products",
            json={
                "name": "Placa de fixação",
                "steps": [
                    {
                        "sequence": 1,
                        "machine_id": custom_machine["id"],
                        "processing_time_seconds": 99,
                    }
                ],
            },
        ).json()
        matching = client.post(
            "/products",
            json={
                "name": "Eixo escalonado",
                "steps": [
                    {"sequence": 1, "machine_id": lathe["id"], "processing_time_seconds": 10},
                    {"sequence": 2, "machine_id": center["id"], "processing_time_seconds": 15},
                ],
            },
        ).json()
    command.upgrade(alembic_config, "head")
    with TestClient(create_app()) as client:
        machines = client.get("/machines").json()
        products = client.get("/products").json()
        assert len(machines) == 5
        assert machines[:4] == [custom_machine, lathe, duplicate, center]
        assert len(products) == 4
        assert products[:2] == [custom_product, matching]
        support = next(product for product in products if product["name"] == "Suporte usinado")
        assert support["steps"][0]["machine_id"] == lathe["id"]
    command.downgrade(alembic_config, "d8e063d489f1")
    command.upgrade(alembic_config, "head")
    with TestClient(create_app()) as client:
        assert client.get("/machines").json() == machines
        assert client.get("/products").json() == products
