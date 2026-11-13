from pathlib import Path
from time import monotonic, sleep
from unittest.mock import Mock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.controllers.planning_controller import get_planning_service, router
from app.schemas.planning_schema import PlanResponse
from app.services.controller_client import CommandStatus, ControllerClient, ControllerStatus, Table
from app.services.execution_service import ExecutionManager
from app.services.planning_service import PlanningService

EXAMPLE = Path(__file__).resolve().parents[2] / "docs" / "examples" / "planning-response.json"


class SimulatedController(ControllerClient):
    def __init__(self, *, wrong_rfid: bool = False) -> None:
        self.occupied = {
            "ARMAZEM_01": True,
            "M1": False,
            "M2": False,
            "M3": False,
            "QA": False,
            "B1": False,
            "B2": False,
            "ESTOQUE_FINAL_01": False,
        }
        self.carried = False
        self.rfid = ""
        self.pieces = {"ARMAZEM_01": "SIM-001", "ARMAZEM_02": "SIM-002"}
        self.buffer_used = False
        self.processing: dict[str, float] = {}
        self.referenced = False
        self.commands: dict[str, CommandStatus] = {}
        self.wrong_rfid = wrong_rfid

    def status(self) -> ControllerStatus:
        return ControllerStatus(
            sessao_id="test",
            mesa=Table(
                referenciada=self.referenced,
                com_peca=self.carried,
                movimento=None,
                cabecote="recolhido",
            ),
            ocupacao=self.occupied,
            falhas=[],
        )

    def command(
        self, command_id: str, kind: str, params: dict[str, object], session: str
    ) -> CommandStatus:
        assert session == "test"
        result = None
        if kind == "referenciar_mesa":
            self.referenced = True
        elif kind == "coletar_peca":
            origin = str(params["origem"])
            if origin == "ARMAZEM":
                origin = next(
                    slot
                    for slot, full in self.occupied.items()
                    if slot.startswith("ARMAZEM_") and full
                )
            assert self.occupied[origin] and not self.carried
            self.occupied[origin] = False
            self.carried = True
            self.rfid = self.pieces.pop(origin)
        elif kind == "depositar_peca":
            target = str(params["destino"])
            if target == "ESTOQUE_FINAL":
                target = next(
                    slot
                    for slot, full in self.occupied.items()
                    if slot.startswith("ESTOQUE_FINAL_") and not full
                )
            assert not self.occupied[target] and self.carried
            self.occupied[target] = True
            self.carried = False
            self.pieces[target] = self.rfid
            self.buffer_used |= target.startswith("B")
        elif kind == "ler_rfid":
            qa = params["ponto"] == "QA"
            assert self.occupied["QA"] if qa else self.carried
            result = {
                "rfid": "DIVERGENTE"
                if qa and self.wrong_rfid
                else self.pieces["QA"]
                if qa
                else self.rfid
            }
        elif kind == "iniciar_processamento":
            self.processing[command_id] = monotonic() + 0.05
        self.commands[command_id] = CommandStatus(
            id=command_id, estado="concluido", resultado=result
        )
        return CommandStatus(id=command_id, estado="aceito")

    def command_status(self, command_id: str) -> CommandStatus:
        if monotonic() < self.processing.get(command_id, 0):
            return CommandStatus(id=command_id, estado="em_execucao")
        return self.commands[command_id]


def run_execution(controller: SimulatedController) -> dict:
    plan = PlanResponse.model_validate_json(EXAMPLE.read_text(encoding="utf-8"))
    first = plan.operations[0]
    plan.operations = [op for op in plan.operations if op.unit_id == first.unit_id]
    mapping = {
        str(machine): station
        for machine, station in zip(
            sorted({op.machine_id for op in plan.operations}), ("M1", "M2", "M3"), strict=False
        )
    }
    service = Mock(spec=PlanningService)
    service.plan.return_value = plan
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_planning_service] = lambda: service
    manager = ExecutionManager(controller, poll_interval=0.001)
    app.state.execution_manager = manager
    try:
        with TestClient(app) as client:
            path = f"/orders/{plan.order_id}/executions"
            response = client.post(path, json={"machine_mapping": mapping})
            assert response.status_code == 202, response.text
            deadline = monotonic() + 3
            while monotonic() < deadline:
                run = client.get(f"{path}/{response.json()['id']}").json()
                if run["state"] in ("completed", "interrupted"):
                    snapshot = client.get("/simulation/status")
                    assert snapshot.status_code == 200
                    assert snapshot.json()["execution"] == run
                    return run
                sleep(0.005)
    finally:
        manager.close()
    raise AssertionError("A execução não terminou no prazo.")


def test_executes_plan_and_tracks_rfid() -> None:
    controller = SimulatedController()
    run = run_execution(controller)
    assert run["state"] == "completed", run
    assert set(run["approved_units"]) == set(run["unit_rfids"])
    assert run["completed_operations"]
    assert controller.occupied["ESTOQUE_FINAL_01"]


def test_buffer_breaks_a_swap_between_occupied_machines() -> None:
    plan = PlanResponse.model_validate_json(EXAMPLE.read_text(encoding="utf-8"))
    first = plan.operations[0]
    specs = [
        ("a1", "a", 1, 0, None),
        ("b1", "b", 2, 0, None),
        ("b2", "b", 1, 10, "b1"),
        ("a2", "a", 2, 10, "a1"),
    ]
    plan.operations = [
        first.model_copy(
            update={
                "operation_id": op,
                "unit_id": unit,
                "machine_id": machine,
                "start_seconds": start,
                "predecessor_operation_id": previous,
            }
        )
        for op, unit, machine, start, previous in specs
    ]
    controller = SimulatedController()
    controller.occupied.update({"ARMAZEM_02": True, "ESTOQUE_FINAL_02": False})
    manager = ExecutionManager(controller, poll_interval=0.001)
    try:
        run = manager.start(plan, {1: "M1", 2: "M2"})
        deadline = monotonic() + 3
        while monotonic() < deadline:
            status = manager.status(run.id)
            if status is not None and status.state in ("completed", "interrupted"):
                break
            sleep(0.005)
        assert status is not None and status.state == "completed", status
        assert set(status.approved_units) == {"a", "b"}
        assert controller.buffer_used
    finally:
        manager.close()


def test_wrong_rfid_uses_shared_output() -> None:
    controller = SimulatedController(wrong_rfid=True)
    run = run_execution(controller)
    assert run["state"] == "completed", run
    assert not run["approved_units"]
    assert "RFID divergente" in next(iter(run["rejected_units"].values()))
    assert not controller.occupied["QA"]
    assert controller.occupied["ESTOQUE_FINAL_01"]
