"""Measure HTTP responsiveness during a real bounded search on a disposable database."""

import argparse
import json
import os
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
from statistics import mean
from threading import Event
from time import monotonic
from uuid import uuid4

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, make_url

from app.config import BACKEND_DIR
from app.services import planning_service

LOCAL_ADMIN_DATABASE_URL = "postgresql+psycopg://axion:axion_local@127.0.0.1:5432/postgres"


@contextmanager
def disposable_database() -> Iterator[None]:
    admin_url = make_url(os.environ.get("AXION_TEST_ADMIN_DATABASE_URL", LOCAL_ADMIN_DATABASE_URL))
    database_name = f"axion_measurement_{uuid4().hex}"
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT", pool_pre_ping=True)
    previous = os.environ.get("AXION_DATABASE_URL")
    created = False
    try:
        with admin_engine.connect() as connection:
            connection.exec_driver_sql(f'CREATE DATABASE "{database_name}"')
        created = True
        os.environ["AXION_DATABASE_URL"] = admin_url.set(database=database_name).render_as_string(
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
                    f'DROP DATABASE IF EXISTS "{database_name}" WITH (FORCE)'
                )
        admin_engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    original = planning_service.plan_problem
    entered = Event()

    def observed(*args: object, **kwargs: object) -> object:
        entered.set()
        return original(*args, **kwargs)

    try:
        with disposable_database():
            from app.main import create_app

            command.upgrade(Config(str(BACKEND_DIR / "alembic.ini")), "head")
            with TestClient(create_app()) as client:
                machines = [
                    client.post("/machines", json={"name": f"M{i}"}).json()["id"] for i in range(50)
                ]
                products = [
                    client.post(
                        "/products",
                        json={
                            "name": f"P{i}",
                            "steps": [
                                {
                                    "sequence": j + 1,
                                    "machine_id": machines[(i * 10 + j) % 50],
                                    "processing_time_seconds": 1 + (i * 7 + j * 13) % 23,
                                }
                                for j in range(10)
                            ],
                        },
                    ).json()["id"]
                    for i in range(10)
                ]
                order = client.post(
                    "/orders", json={"items": [{"product_id": p, "quantity": 10} for p in products]}
                ).json()["id"]

                def sample() -> float:
                    started = monotonic()
                    response = client.get("/machines")
                    if response.status_code != 200:
                        raise RuntimeError(response.text)
                    return monotonic() - started

                baseline = [sample() for _ in range(20)]
                planning_service.plan_problem = observed
                with ThreadPoolExecutor() as executor:
                    future = executor.submit(client.post, f"/orders/{order}/plan", json={})
                    if not entered.wait(10):
                        raise RuntimeError("Search did not start")
                    started = monotonic()
                    busy = client.post(f"/orders/{order}/plan", json={})
                    busy_seconds = monotonic() - started
                    during = []
                    while not future.done():
                        during.append(sample())
                        Event().wait(0.2)
                    response = future.result()
                result = response.json()
                if response.status_code == 409:
                    result = result["result"]
                if response.status_code not in {200, 409} or busy.status_code != 503:
                    raise RuntimeError("Unexpected response")
                report = dict(
                    measurement="TestClient, one process, real GA/CP-SAT, disposable PostgreSQL",
                    baseline_get_machines=dict(
                        samples=len(baseline),
                        mean_seconds=mean(baseline),
                        worst_seconds=max(baseline),
                    ),
                    during_search_get_machines=dict(
                        samples=len(during), mean_seconds=mean(during), worst_seconds=max(during)
                    ),
                    busy_status=busy.status_code,
                    busy_seconds=busy_seconds,
                    planning_status=response.status_code,
                    search=result["search"],
                    metrics=result["metrics"],
                )
                args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    finally:
        planning_service.plan_problem = original


if __name__ == "__main__":
    main()
