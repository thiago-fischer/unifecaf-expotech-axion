from __future__ import annotations

import json
from uuid import uuid4

import psycopg
import pytest
from psycopg import errors, sql
from sqlalchemy import URL

from app.config import BACKEND_DIR
from scripts.prepare_grafana_reader import connection_parameters, prepare_reader

DASHBOARD_PATH = (
    BACKEND_DIR.parent / "infrastructure" / "grafana" / "dashboards" / "dados-persistidos.json"
)


def reader_parameters(database_url: URL, user: str, password: str) -> dict[str, object]:
    _, parameters = connection_parameters(database_url.render_as_string(hide_password=False))
    return {**parameters, "user": user, "password": password}


def test_grafana_role_is_idempotent_and_read_only(migrated_database: URL) -> None:
    reader = f"grafana_test_{uuid4().hex}"
    future_table = f"grafana_future_{uuid4().hex}"
    first_password = f"first_{uuid4().hex}"
    second_password = f"second_{uuid4().hex}"
    _, admin_parameters = connection_parameters(
        migrated_database.render_as_string(hide_password=False)
    )
    assert migrated_database.database is not None
    assert migrated_database.username is not None

    with psycopg.connect(**admin_parameters) as admin:
        try:
            prepare_reader(
                admin,
                database=migrated_database.database,
                owner=migrated_database.username,
                reader=reader,
                password=first_password,
            )
            with admin.cursor() as cursor:
                cursor.execute(
                    sql.SQL("CREATE TABLE {} (id integer)").format(sql.Identifier(future_table))
                )
            admin.commit()

            with psycopg.connect(
                **reader_parameters(migrated_database, reader, first_password)
            ) as connection:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT COUNT(*) FROM machines")
                    assert cursor.fetchone() == (3,)
                    dashboard = json.loads(DASHBOARD_PATH.read_text(encoding="utf-8"))
                    for panel in dashboard["panels"]:
                        cursor.execute(panel["targets"][0]["rawSql"])
                        cursor.fetchall()
                    cursor.execute("SELECT COUNT(*) FROM network_metric_samples")
                    assert cursor.fetchone() == (0,)

                for forbidden_table in (future_table, "network_capture_batches"):
                    with connection.cursor() as cursor, pytest.raises(errors.InsufficientPrivilege):
                        cursor.execute(
                            sql.SQL("SELECT * FROM {}").format(sql.Identifier(forbidden_table))
                        )
                    connection.rollback()

                mutations = (
                    "INSERT INTO machines (name) VALUES ('Não permitida')",
                    "UPDATE machines SET name = 'Não permitida'",
                    "DELETE FROM machines",
                    "TRUNCATE TABLE machines",
                    "CREATE TABLE grafana_must_not_create (id integer)",
                )
                for statement in mutations:
                    with connection.cursor() as cursor, pytest.raises(errors.InsufficientPrivilege):
                        cursor.execute(statement)
                    connection.rollback()

            prepare_reader(
                admin,
                database=migrated_database.database,
                owner=migrated_database.username,
                reader=reader,
                password=second_password,
            )
            with psycopg.connect(
                **reader_parameters(migrated_database, reader, second_password)
            ) as connection:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT COUNT(*) FROM products")
                    assert cursor.fetchone() == (3,)

            with admin.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT rolsuper, rolcreatedb, rolcreaterole, rolreplication, rolbypassrls
                    FROM pg_roles
                    WHERE rolname = %s
                    """,
                    (reader,),
                )
                assert cursor.fetchone() == (False, False, False, False, False)
        finally:
            admin.rollback()
            with admin.cursor() as cursor:
                cursor.execute(
                    sql.SQL("DROP TABLE IF EXISTS {}").format(sql.Identifier(future_table))
                )
                cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (reader,))
                if cursor.fetchone() is not None:
                    cursor.execute(
                        sql.SQL(
                            "ALTER DEFAULT PRIVILEGES FOR ROLE {} IN SCHEMA public "
                            "REVOKE SELECT ON TABLES FROM {}"
                        ).format(sql.Identifier(migrated_database.username), sql.Identifier(reader))
                    )
                    cursor.execute(sql.SQL("DROP OWNED BY {}").format(sql.Identifier(reader)))
                    cursor.execute(sql.SQL("DROP ROLE {}").format(sql.Identifier(reader)))
            admin.commit()


def test_grafana_role_cannot_reuse_application_owner(migrated_database: URL) -> None:
    _, admin_parameters = connection_parameters(
        migrated_database.render_as_string(hide_password=False)
    )
    assert migrated_database.database is not None
    assert migrated_database.username is not None
    with (
        psycopg.connect(**admin_parameters) as connection,
        pytest.raises(RuntimeError, match="não pode reutilizar"),
    ):
        prepare_reader(
            connection,
            database=migrated_database.database,
            owner=migrated_database.username,
            reader=migrated_database.username,
            password="local",
        )
