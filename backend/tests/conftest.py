import os
from collections.abc import Iterator
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import URL, create_engine, make_url
from sqlalchemy.orm import Session, sessionmaker

TEST_ADMIN_DATABASE_URL = os.environ.get(
    "AXION_TEST_ADMIN_DATABASE_URL",
    "postgresql+psycopg://axion:axion_local@127.0.0.1:5432/postgres",
)
os.environ.setdefault("AXION_DATABASE_URL", TEST_ADMIN_DATABASE_URL)

# The application creates its engine at import time, so tests must provide a valid
# PostgreSQL URL before importing application modules.
from app.config import BACKEND_DIR, Settings  # noqa: E402
from app.database.database import build_engine  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models import Machine, Product, ProductStep  # noqa: E402


@pytest.fixture
def database_url(monkeypatch: pytest.MonkeyPatch) -> Iterator[URL]:
    admin_url = make_url(TEST_ADMIN_DATABASE_URL)
    database_name = f"axion_test_{uuid4().hex}"
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT", pool_pre_ping=True)
    try:
        with admin_engine.connect() as connection:
            connection.exec_driver_sql(f'CREATE DATABASE "{database_name}"')
        test_url = admin_url.set(database=database_name)
        monkeypatch.setenv("AXION_DATABASE_URL", test_url.render_as_string(hide_password=False))
        yield test_url
    finally:
        with admin_engine.connect() as connection:
            connection.exec_driver_sql(f'DROP DATABASE IF EXISTS "{database_name}" WITH (FORCE)')
        admin_engine.dispose()


@pytest.fixture
def alembic_config(database_url: URL) -> Config:
    return Config(str(BACKEND_DIR / "alembic.ini"))


@pytest.fixture
def migrated_database(alembic_config: Config, database_url: URL) -> URL:
    command.upgrade(alembic_config, "head")
    return database_url


@pytest.fixture
def empty_database(migrated_database: URL) -> URL:
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
def session(empty_database: URL) -> Iterator[Session]:
    engine = build_engine(Settings())
    try:
        with sessionmaker(engine, expire_on_commit=False)() as session:
            yield session
    finally:
        engine.dispose()


@pytest.fixture
def client(empty_database: URL) -> Iterator[TestClient]:
    with TestClient(create_app()) as client:
        yield client
