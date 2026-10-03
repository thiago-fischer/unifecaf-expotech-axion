from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.config import BACKEND_DIR, Settings
from app.database.database import build_engine
from app.main import create_app
from app.models import Machine, Product, ProductStep


@pytest.fixture
def database_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "test.db"
    monkeypatch.setenv("AXION_DATABASE_PATH", str(path))
    return path


@pytest.fixture
def alembic_config(database_path: Path) -> Config:
    return Config(str(BACKEND_DIR / "alembic.ini"))


@pytest.fixture
def migrated_database(alembic_config: Config, database_path: Path) -> Path:
    command.upgrade(alembic_config, "head")
    return database_path


@pytest.fixture
def empty_database(migrated_database: Path) -> Path:
    """Exercise empty-catalog contracts after applying the complete migration history."""
    engine = build_engine(Settings())
    try:
        with engine.begin() as connection:
            connection.execute(ProductStep.__table__.delete())
            connection.execute(Product.__table__.delete())
            connection.execute(Machine.__table__.delete())
    finally:
        engine.dispose()
    return migrated_database


@pytest.fixture
def session(empty_database: Path) -> Iterator[Session]:
    engine = build_engine(Settings())
    try:
        with sessionmaker(engine, expire_on_commit=False)() as session:
            yield session
    finally:
        engine.dispose()


@pytest.fixture
def client(empty_database: Path) -> Iterator[TestClient]:
    with TestClient(create_app()) as client:
        yield client
