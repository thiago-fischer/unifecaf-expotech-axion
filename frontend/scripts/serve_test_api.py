"""API real com migrations em banco descartável para os testes de navegador."""

import os
import subprocess
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import uvicorn
from sqlalchemy import create_engine, make_url, text

LOCAL_ADMIN_DATABASE_URL = "postgresql+psycopg://axion:axion_local@127.0.0.1:5432/postgres"
DATABASE_NAME = "axion_frontend_e2e"


def quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


@contextmanager
def disposable_database() -> Iterator[None]:
    admin_url = make_url(os.environ.get("AXION_TEST_ADMIN_DATABASE_URL", LOCAL_ADMIN_DATABASE_URL))
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT", pool_pre_ping=True)
    previous = os.environ.get("AXION_DATABASE_URL")
    created = False
    try:
        with admin_engine.connect() as connection:
            stale_databases = list(
                connection.execute(
                    text("SELECT datname FROM pg_database WHERE datname LIKE :pattern"),
                    {"pattern": "axion_frontend_e2e%"},
                ).scalars()
            )
            for database_name in stale_databases:
                connection.exec_driver_sql(
                    f"DROP DATABASE IF EXISTS {quote_identifier(database_name)} WITH (FORCE)"
                )
            connection.exec_driver_sql(f"CREATE DATABASE {quote_identifier(DATABASE_NAME)}")
        created = True
        os.environ["AXION_DATABASE_URL"] = admin_url.set(database=DATABASE_NAME).render_as_string(
            hide_password=False
        )
        yield
    finally:
        if previous is None:
            os.environ.pop("AXION_DATABASE_URL", None)
        else:
            os.environ["AXION_DATABASE_URL"] = previous
        if created:
            with admin_engine.connect() as connection:
                connection.exec_driver_sql(
                    f"DROP DATABASE IF EXISTS {quote_identifier(DATABASE_NAME)} WITH (FORCE)"
                )
        admin_engine.dispose()


def main() -> None:
    backend = Path(__file__).resolve().parents[2] / "backend"
    with disposable_database():
        subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"], cwd=backend, check=True
        )
        uvicorn.run("app.main:app", host="127.0.0.1", port=8765)


if __name__ == "__main__":
    main()
