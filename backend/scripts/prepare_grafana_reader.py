"""Prepare the PostgreSQL role used by the local Grafana datasource."""

from __future__ import annotations

import os
from collections.abc import Sequence

import psycopg
from psycopg import Connection, sql
from sqlalchemy.engine import URL, make_url

DATABASE_URL_ENV = "AXION_DATABASE_URL"
GRAFANA_USER_ENV = "GRAFANA_DB_USER"
GRAFANA_PASSWORD_ENV = "GRAFANA_DB_PASSWORD"
DOMAIN_TABLES = (
    "machines",
    "products",
    "product_steps",
    "production_orders",
    "production_order_items",
    "network_metric_samples",
)


def required_environment(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise RuntimeError(f"Defina {name} para preparar o acesso do Grafana.")
    return value


def connection_parameters(database_url: str) -> tuple[URL, dict[str, object]]:
    try:
        url = make_url(database_url)
    except Exception as exc:
        raise RuntimeError(f"{DATABASE_URL_ENV} contém uma URL inválida.") from exc
    if url.drivername != "postgresql+psycopg":
        raise RuntimeError(f"{DATABASE_URL_ENV} deve usar o driver postgresql+psycopg.")
    if not url.host or not url.database or not url.username:
        raise RuntimeError(f"{DATABASE_URL_ENV} deve informar host, banco e usuário do PostgreSQL.")
    return url, {
        "host": url.host,
        "port": url.port or 5432,
        "dbname": url.database,
        "user": url.username,
        "password": url.password or "",
    }


def prepare_reader(
    connection: Connection,
    *,
    database: str,
    owner: str,
    reader: str,
    password: str,
    tables: Sequence[str] = DOMAIN_TABLES,
) -> None:
    if not reader or not password:
        raise RuntimeError("Usuário e senha do Grafana devem ser informados.")
    if reader == owner:
        raise RuntimeError("O Grafana não pode reutilizar o usuário proprietário da aplicação.")

    reader_id = sql.Identifier(reader)
    with connection.transaction(), connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (reader,))
        if cursor.fetchone() is None:
            cursor.execute(
                sql.SQL(
                    "CREATE ROLE {} WITH LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB "
                    "NOCREATEROLE NOREPLICATION NOBYPASSRLS"
                ).format(reader_id, sql.Literal(password))
            )
        else:
            cursor.execute(
                sql.SQL(
                    "ALTER ROLE {} WITH LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB "
                    "NOCREATEROLE NOREPLICATION NOBYPASSRLS"
                ).format(reader_id, sql.Literal(password))
            )

        cursor.execute(
            """
            SELECT granted.rolname
            FROM pg_auth_members membership
            JOIN pg_roles granted ON granted.oid = membership.roleid
            JOIN pg_roles member ON member.oid = membership.member
            WHERE member.rolname = %s
            """,
            (reader,),
        )
        for (granted_role,) in cursor.fetchall():
            cursor.execute(
                sql.SQL("REVOKE {} FROM {}").format(sql.Identifier(granted_role), reader_id)
            )

        cursor.execute(
            sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
                sql.Identifier(database), reader_id
            )
        )
        cursor.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(reader_id))
        cursor.execute(sql.SQL("ALTER ROLE {} SET search_path TO public").format(reader_id))

        cursor.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename"
        )
        approved = set(tables)
        for (table,) in cursor.fetchall():
            table_id = sql.Identifier("public", table)
            cursor.execute(
                sql.SQL("REVOKE ALL PRIVILEGES ON TABLE {} FROM {}").format(table_id, reader_id)
            )
            if table in approved:
                cursor.execute(
                    sql.SQL("GRANT SELECT ON TABLE {} TO {}").format(table_id, reader_id)
                )

        cursor.execute(
            sql.SQL(
                "ALTER DEFAULT PRIVILEGES FOR ROLE {} IN SCHEMA public "
                "REVOKE SELECT ON TABLES FROM {}"
            ).format(sql.Identifier(owner), reader_id)
        )


def main() -> None:
    database_url = required_environment(DATABASE_URL_ENV)
    reader = required_environment(GRAFANA_USER_ENV)
    password = required_environment(GRAFANA_PASSWORD_ENV)
    url, parameters = connection_parameters(database_url)
    assert url.database is not None and url.username is not None
    with psycopg.connect(**parameters) as connection:
        prepare_reader(
            connection,
            database=url.database,
            owner=url.username,
            reader=reader,
            password=password,
        )
    print(f"Acesso somente leitura preparado para {reader} no banco {url.database}.")


if __name__ == "__main__":
    main()
