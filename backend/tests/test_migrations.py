from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import inspect

from app.config import BACKEND_DIR, Settings
from app.database.database import build_engine
from app.main import create_app


def test_upgrade_repeat_downgrade_and_upgrade(alembic_config: Config) -> None:
    command.upgrade(alembic_config, "head")
    with TestClient(create_app()) as client:
        assert client.get("/machines").json() == []
        machine = client.post("/machines", json={"name": "Migration"}).json()
    command.upgrade(alembic_config, "head")
    command.check(alembic_config)
    with TestClient(create_app()) as client:
        assert client.get("/machines").json() == [machine]
    command.downgrade(alembic_config, "base")
    engine = build_engine(Settings())
    try:
        assert "machines" not in inspect(engine).get_table_names()
    finally:
        engine.dispose()
    command.upgrade(alembic_config, "head")
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
