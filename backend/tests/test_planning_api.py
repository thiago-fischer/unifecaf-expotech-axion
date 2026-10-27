import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event

import pytest
from axion_optimizer import planner
from axion_optimizer.certification import Certification
from axion_optimizer.domain import Item, Machine, Snapshot, Step, prepare
from axion_optimizer.validation import validate_result
from fastapi.testclient import TestClient
from sqlalchemy import event, inspect
from sqlalchemy.exc import OperationalError

from app.repositories.planning_repository import PlanningRepository
from app.schemas.planning_schema import PlanResponse
from app.services import planning_service


def create_order(client: TestClient, quantity: int = 1, steps: int = 2) -> int:
    m1 = client.post("/machines", json={"name": "Repetido"}).json()["id"]
    m2 = client.post("/machines", json={"name": "Repetido"}).json()["id"]
    # Opposing routes: analytical load bound is weaker than the optimum.
    products = [
        client.post(
            "/products",
            json={
                "name": "Repetido",
                "steps": [
                    {
                        "sequence": i,
                        "machine_id": (m1 if i % 2 else m2),
                        "processing_time_seconds": 10,
                    }
                    for i in range(1, steps + 1)
                ],
            },
        ).json()
        for _ in range(2)
    ]
    return client.post(
        "/orders", json={"items": [{"product_id": p["id"], "quantity": quantity} for p in products]}
    ).json()["id"]


def test_plan_new_catalog_and_no_writes(client: TestClient) -> None:
    order = create_order(client)
    before = {path: client.get(path).json() for path in ["/orders", "/products", "/machines"]}
    for _ in range(2):
        response = client.post(f"/orders/{order}/plan", json={})
        assert response.status_code == 200, response.text
        result = PlanResponse.model_validate(response.json())
        assert result.quality == "optimal"
        assert result.metrics.makespan_seconds == 30
        assert result.search.ga.evaluations > 0
        assert result.execution_ready is False
        assert result.search.certification.num_search_workers == 1
        assert result.search.certification.absolute_gap_limit == 0
        assert result.search.certification.relative_gap_limit == 0
        assert result.proof.solver_version != "illustrative-not-executed"
        assert all(
            o.predecessor_operation_id is not None for o in result.operations if o.step_sequence > 1
        )
        assert {m.machine_id for m in result.machine_metrics} == {
            m.machine_id for m in result.input_snapshot.machines
        }
    for path, data in before.items():
        assert client.get(path).json() == data
    another = create_order(client, 2, 3)
    response = client.post(f"/orders/{another}/plan", json={"seed": 21})
    assert response.status_code == 200
    assert response.json()["metrics"]["operation_count"] == 12
    with client.app.state.session_factory() as session:
        assert set(inspect(session.get_bind()).get_table_names()) == {
            "alembic_version",
            "machines",
            "products",
            "product_steps",
            "production_orders",
            "production_order_items",
            "progress_events",
        }


@pytest.mark.parametrize(
    "policy,status", [(None, 409), ("require_proof", 409), ("allow_feasible", 200)]
)
def test_unproven_policy(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, policy: str | None, status: int
) -> None:
    order = create_order(client)
    monkeypatch.setattr(planner, "certify", lambda *args: Certification("UNKNOWN", None, 0, 0))
    response = client.post(
        f"/orders/{order}/plan", json={} if policy is None else {"optimality_policy": policy}
    )
    assert response.status_code == status
    result = response.json()
    if status == 409:
        assert result["code"] == "optimality_not_proven"
        result = result["result"]
    parsed = PlanResponse.model_validate(result)
    assert parsed.quality == "feasible"
    assert parsed.proof.method == "none"
    assert parsed.metrics.absolute_gap_seconds > 0


@pytest.mark.parametrize(
    "field", ["seed", "ga_time_limit_seconds", "certification_time_limit_seconds"]
)
@pytest.mark.parametrize("value", [True, False, 1.0, "1", None, [], {}, -1])
def test_strict_input(client: TestClient, field: str, value: object) -> None:
    assert client.post("/orders/1/plan", json={field: value}).status_code == 422


@pytest.mark.parametrize("ga,cp,seed", [(1, 1, 0), (20, 10, 2_147_483_647), (10, 20, 0)])
def test_budget_and_seed_boundaries(client: TestClient, ga: int, cp: int, seed: int) -> None:
    order = create_order(client)
    response = client.post(
        f"/orders/{order}/plan",
        json={"ga_time_limit_seconds": ga, "certification_time_limit_seconds": cp, "seed": seed},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["search"]["ga"]["time_limit_seconds"] == ga
    assert result["search"]["certification"]["time_limit_seconds"] == cp
    assert result["search"]["certification"]["seed"] == seed


@pytest.mark.parametrize(
    "data",
    [
        None,
        [],
        "a",
        {"extra": 1},
        {"seed": 2_147_483_648},
        {"ga_time_limit_seconds": 0},
        {"ga_time_limit_seconds": 21},
        {"certification_time_limit_seconds": 0},
        {"certification_time_limit_seconds": 21},
        {"ga_time_limit_seconds": 20, "certification_time_limit_seconds": 11},
        {"optimality_policy": None},
        {"optimality_policy": "optimal"},
    ],
)
def test_invalid_request(client: TestClient, data: object) -> None:
    assert client.post("/orders/1/plan", json=data).status_code == 422


def test_path_and_absence(client: TestClient) -> None:
    assert client.post("/orders/1/plan").status_code == 422
    for value in ["0", "-1", "abc", "1.0"]:
        assert client.post(f"/orders/{value}/plan", json={}).status_code == 422
    for value in [1, 2**64]:
        response = client.post(f"/orders/{value}/plan", json={})
        assert response.status_code == 404
        assert response.json() == {"detail": "Ordem de produção não encontrada."}


def test_limits_prior_to_search(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    order = create_order(client, quantity=1000)

    def fail(*args: object, **kwargs: object) -> None:
        pytest.fail("Search must not start")

    monkeypatch.setattr(planning_service, "plan_problem", fail)
    response = client.post(f"/orders/{order}/plan", json={})
    assert response.status_code == 422
    assert response.json() == {
        "detail": "A ordem excede os limites de planejamento.",
        "code": "planning_limits_exceeded",
        "violations": [
            {"field": "operation_count", "actual": 4000, "limit": 1000},
            {"field": "unit_count", "actual": 2000, "limit": 100},
        ],
    }


@pytest.mark.parametrize("mode", ["solver", "invalid_plan", "database", "snapshot"])
def test_failure_and_release(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, mode: str, caplog: pytest.LogCaptureFixture
) -> None:
    order = create_order(client)
    with monkeypatch.context() as patch:

        def fail(*args: object, **kwargs: object) -> None:
            raise RuntimeError("diagnóstico privado")

        if mode == "solver":
            patch.setattr(planner, "certify", fail)
        elif mode == "invalid_plan":
            patch.setattr(planner, "certify", lambda *args: Certification("FEASIBLE", (), 0, 0))
        elif mode == "database":

            def db_fail(*args: object) -> None:
                raise OperationalError("diagnóstico privado", {}, Exception("failure"))

            patch.setattr(PlanningRepository, "snapshot", db_fail)
        else:
            patch.setattr(PlanningRepository, "snapshot", lambda *args: Snapshot((), ()))
        response = client.post(f"/orders/{order}/plan", json={})
        assert response.status_code == 500
        assert response.json() == {"detail": "Erro interno do servidor."}
        assert "Falha no planejamento" in caplog.text
    assert client.post(f"/orders/{order}/plan", json={}).status_code == 200


def test_concurrency_session_release_and_other_routes(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    order = create_order(client)
    entered, resume = Event(), Event()
    original = planning_service.plan_problem
    factory = client.app.state.session_factory
    engine = factory.kw["bind"]

    def blocked(problem: object, *args: object, **kwargs: object) -> object:
        # SQLAlchemy has returned all connections before the first solver call.
        assert engine.pool.checkedout() == 0
        entered.set()
        assert resume.wait(10)
        return original(problem, *args, **kwargs)

    monkeypatch.setattr(planning_service, "plan_problem", blocked)
    with ThreadPoolExecutor() as executor:
        first = executor.submit(client.post, f"/orders/{order}/plan", json={})
        try:
            assert entered.wait(5)
            response = client.post(f"/orders/{order}/plan", json={})
            assert response.status_code == 503
            assert response.headers["Retry-After"] == "1"
            assert response.json()["code"] == "planning_busy"
            assert client.get("/machines").status_code == 200
            # A second app instance in this process must share the lock.
            from app.main import create_app

            with TestClient(create_app()) as other:
                assert other.post(f"/orders/{order}/plan", json={}).status_code == 503
            assert client.post("/orders/999999/plan", json={}).status_code == 404
        finally:
            resume.set()
        assert first.result(10).status_code == 200
    assert client.post(f"/orders/{order}/plan", json={}).status_code == 200


def test_no_sql_during_search(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    order = create_order(client)
    engine = client.app.state.session_factory.kw["bind"]
    original = planning_service.plan_problem

    def protected(*args: object, **kwargs: object) -> object:
        def reject(*args: object) -> None:
            pytest.fail("SQL during optimization")

        event.listen(engine, "before_cursor_execute", reject)
        try:
            return original(*args, **kwargs)
        finally:
            event.remove(engine, "before_cursor_execute", reject)

    monkeypatch.setattr(planning_service, "plan_problem", protected)
    assert client.post(f"/orders/{order}/plan", json={}).status_code == 200


def test_documentary_schema_and_openapi(client: TestClient) -> None:
    root = Path(__file__).resolve().parents[2]
    data = json.loads((root / "docs/examples/planning-response.json").read_text(encoding="utf-8"))
    response = PlanResponse.model_validate(data)
    snapshot = Snapshot(
        tuple(
            Item(
                i.product_id,
                i.product_name,
                i.quantity,
                tuple(Step(s.sequence, s.machine_id, s.processing_time_seconds) for s in i.steps),
            )
            for i in response.input_snapshot.items
        ),
        tuple(Machine(m.machine_id, m.machine_name) for m in response.input_snapshot.machines),
    )
    validate_result(prepare(snapshot), response.model_dump())
    operation = client.get("/openapi.json").json()["paths"]["/orders/{order_id}/plan"]["post"]
    assert set(operation["responses"]) == {"200", "404", "409", "422", "500", "503"}
    assert operation["requestBody"]["required"]
