from pathlib import Path
from unittest.mock import Mock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.controllers.planning_controller import get_planning_service, router
from app.schemas.planning_schema import PlanRequest, PlanResponse
from app.services.planning_service import PlanningService

EXAMPLE = Path(__file__).resolve().parents[2] / "docs" / "examples" / "planning-response.json"


def test_queues_group_and_order_operations_preserving_unit_dependencies() -> None:
    plan = PlanResponse.model_validate_json(EXAMPLE.read_text(encoding="utf-8"))
    plan.operations.reverse()
    service = Mock(spec=PlanningService)
    service.plan.return_value = plan
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_planning_service] = lambda: service

    with TestClient(app) as client:
        response = client.post(f"/orders/{plan.order_id}/plan/queues", json={})
        assert response.status_code == 200, response.text
        original = client.post(f"/orders/{plan.order_id}/plan", json={})
        assert original.json() == plan.model_dump(mode="json")

    body = response.json()
    assert body["order_id"] == plan.order_id
    assert body["execution_ready"] is False
    queues = body["machine_queues"]
    assert len(queues) > 1
    assert any(len(queue["operations"]) > 1 for queue in queues)
    assert [queue["machine_id"] for queue in queues] == sorted(
        {operation.machine_id for operation in plan.operations}
    )
    for queue in queues:
        expected = sorted(
            (op for op in plan.operations if op.machine_id == queue["machine_id"]),
            key=lambda op: op.start_seconds,
        )
        assert queue["operations"] == [op.model_dump(mode="json") for op in expected]
    assert any(op.predecessor_operation_id for op in plan.operations)
    service.plan.assert_called_with(plan.order_id, PlanRequest())


def test_queues_respect_the_requested_optimality_policy() -> None:
    plan = PlanResponse.model_validate_json(EXAMPLE.read_text(encoding="utf-8"))
    plan.optimality_proven = False
    service = Mock(spec=PlanningService)
    service.plan.return_value = plan
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_planning_service] = lambda: service
    path = f"/orders/{plan.order_id}/plan/queues"

    with TestClient(app) as client:
        response = client.post(path, json={})
        assert response.status_code == 409
        assert response.json()["code"] == "optimality_not_proven"
        response = client.post(path, json={"optimality_policy": "allow_feasible"})
        assert response.status_code == 200
        assert response.json()["execution_ready"] is False
