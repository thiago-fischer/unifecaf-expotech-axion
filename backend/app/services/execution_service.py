import logging
from collections import deque
from dataclasses import dataclass
from threading import Event, Lock, Thread
from time import monotonic
from uuid import uuid4

from app.schemas.execution_schema import ExecutionStatus, Station
from app.schemas.planning_schema import PlanOperation, PlanResponse
from app.services.controller_client import ControllerClient, ControllerError, ControllerStatus
from app.services.planning_service import build_machine_queues

logger = logging.getLogger(__name__)


class ExecutionBusy(Exception):
    pass


class InvalidExecution(ValueError):
    pass


@dataclass
class Unit:
    position: str
    remaining: int
    rfid: str | None = None


@dataclass(frozen=True)
class Processing:
    command_id: str
    deadline: float


class ExecutionManager:
    def __init__(self, controller: ControllerClient, poll_interval: float = 0.1) -> None:
        self.controller = controller
        self.poll_interval = poll_interval
        self._stop = Event()
        self._lock = Lock()
        self._worker: Thread | None = None
        self._runs: dict[str, ExecutionStatus] = {}

    def start(self, plan: PlanResponse, mapping: dict[int, Station]) -> ExecutionStatus:
        queues = build_machine_queues(plan).machine_queues
        if {queue.machine_id for queue in queues} - mapping.keys():
            raise InvalidExecution("Informe a estação de cada máquina usada no plano.")
        if len(set(mapping.values())) != len(mapping):
            raise InvalidExecution("Cada máquina deve ter uma estação distinta.")
        if not 1 <= len({op.unit_id for op in plan.operations}) <= 10:
            raise InvalidExecution("A execução simulada requer de 1 a 10 peças.")
        if any(op.duration_seconds * 1000 > 2_147_483_647 for op in plan.operations):
            raise InvalidExecution("Uma etapa excede a duração aceita pelo controlador.")

        with self._lock:
            if self._stop.is_set() or (self._worker is not None and self._worker.is_alive()):
                raise ExecutionBusy
            run = ExecutionStatus(id=uuid4().hex, order_id=plan.order_id, state="queued")
            self._runs[run.id] = run
            execution = Execution(
                self,
                run.id,
                {mapping[queue.machine_id]: deque(queue.operations) for queue in queues},
            )
            self._worker = Thread(target=execution.run, daemon=True, name=f"axion-{run.id}")
            self._worker.start()
            return run.model_copy(deep=True)

    def status(self, run_id: str) -> ExecutionStatus | None:
        with self._lock:
            run = self._runs.get(run_id)
            return run.model_copy(deep=True) if run is not None else None

    def close(self) -> None:
        with self._lock:
            self._stop.set()
            worker = self._worker
        if worker is not None:
            worker.join()


class Execution:
    def __init__(
        self, manager: ExecutionManager, run_id: str, queues: dict[Station, deque[PlanOperation]]
    ) -> None:
        self.manager = manager
        self.controller = manager.controller
        self.run_id = run_id
        self.queues = queues
        self.session: str | None = None
        self.next_command = 0
        self.units: dict[str, Unit] = {}
        self.processing: dict[Station, Processing] = {}
        self.completed: set[str] = set()
        self.rfids: set[str] = set()
        self.output: deque[str] = deque()

    def run(self) -> None:
        try:
            with self.manager._lock:
                self.manager._runs[self.run_id].state = "running"
            self._initialize()
            while self.units:
                status = self._status()
                self._finish_processing()
                if self._dispatch(status):
                    continue
                if not self.processing:
                    raise ControllerError("Execução bloqueada: nenhuma peça pode avançar.")
                self._wait()
        except ControllerError as exc:
            self._finish("interrupted", str(exc))
        except Exception:
            logger.exception("Falha na execução %s", self.run_id)
            self._finish("interrupted", "Erro interno durante a execução.")
        else:
            self._finish("completed")

    def _finish(self, state: str, reason: str | None = None) -> None:
        with self.manager._lock:
            run = self.manager._runs[self.run_id]
            run.state = state
            run.reason = reason

    def _initialize(self) -> None:
        status = self._status()
        self.session = status.sessao_id
        if (
            status.mesa.com_peca
            or status.mesa.movimento is not None
            or status.mesa.cabecote != "recolhido"
            or any(
                status.ocupacao.get(station) is not False for station in ("M1", "M2", "M3", "QA")
            )
        ):
            raise ControllerError("A execução requer mesa e estações livres no início.")

        counts: dict[str, int] = {}
        for queue in self.queues.values():
            for op in queue:
                counts[op.unit_id] = counts.get(op.unit_id, 0) + 1
        warehouse = sorted(
            slot
            for slot, occupied in status.ocupacao.items()
            if slot.startswith("ARMAZEM_") and occupied
        )
        self.output = deque(
            sorted(
                slot
                for slot, occupied in status.ocupacao.items()
                if slot.startswith("ESTOQUE_FINAL_") and not occupied
            )
        )
        if len(warehouse) < len(counts) or len(self.output) < len(counts):
            raise ControllerError("Peças no armazém ou vagas no estoque final insuficientes.")
        self.units = {
            unit_id: Unit(slot, counts[unit_id])
            for unit_id, slot in zip(counts, warehouse, strict=False)
        }
        if not status.mesa.referenciada:
            self._table("referenciar_mesa")

    def _dispatch(self, status: ControllerStatus) -> bool:
        if status.ocupacao.get("QA") is False:
            for unit_id, unit in self.units.items():
                if unit.remaining == 0:
                    self._approve(unit_id, unit)
                    return True

        ready: list[tuple[Station, PlanOperation]] = []
        for station, queue in self.queues.items():
            if not queue or station in self.processing:
                continue
            operation = queue[0]
            unit = self.units[operation.unit_id]
            previous = operation.predecessor_operation_id
            if previous is not None and previous not in self.completed:
                continue
            if unit.position == station or status.ocupacao.get(station) is False:
                ready.append((station, operation))
        if not ready:
            return False
        station, operation = min(
            ready,
            key=lambda item: (
                self.units[item[1].unit_id].rfid is None,
                item[1].start_seconds,
                item[1].operation_id,
            ),
        )
        unit = self.units[operation.unit_id]
        continuing = unit.position == station
        if not continuing:
            self._table("coletar_peca", origem=unit.position)
            if unit.rfid is None:
                self._table("mover_para", destino="LEITOR_RFID")
                unit.rfid = self._read("LEITOR_RFID")
                if unit.rfid in self.rfids:
                    raise ControllerError("RFID já associado a outra unidade da OP.")
                self.rfids.add(unit.rfid)
                with self.manager._lock:
                    self.manager._runs[self.run_id].unit_rfids[operation.unit_id] = unit.rfid
            self._table("depositar_peca", destino=station)
            unit.position = station
        command_id = self._send(
            "iniciar_processamento",
            maquina_id=station,
            duracao_ms=operation.duration_seconds * 1000,
            **({"continuar_na_maquina": True} if continuing else {}),
        )
        self.processing[station] = Processing(
            command_id, monotonic() + operation.duration_seconds + 10
        )
        return True

    def _finish_processing(self) -> None:
        for station, active in tuple(self.processing.items()):
            result = self._command_result(active.command_id, active.deadline)
            if result is None:
                continue
            operation = self.queues[station].popleft()
            self.completed.add(operation.operation_id)
            self.units[operation.unit_id].remaining -= 1
            del self.processing[station]
            with self.manager._lock:
                self.manager._runs[self.run_id].completed_operations.append(operation.operation_id)

    def _approve(self, unit_id: str, unit: Unit) -> None:
        self._table("coletar_peca", origem=unit.position)
        self._table("depositar_peca", destino="QA")
        if self._read("QA") != unit.rfid:
            raise ControllerError(f"RFID divergente no QA para a unidade {unit_id}.")
        self._table("coletar_peca", origem="QA")
        self._table("depositar_peca", destino=self.output.popleft())
        del self.units[unit_id]
        with self.manager._lock:
            self.manager._runs[self.run_id].approved_units.append(unit_id)

    def _read(self, point: str) -> str:
        result = self._table("ler_rfid", ponto=point)
        if not result.get("rfid"):
            raise ControllerError("Controlador concluiu a leitura sem RFID.")
        return result["rfid"]

    def _table(self, kind: str, **params: object) -> dict[str, str]:
        command_id = self._send(kind, **params)
        deadline = monotonic() + 10
        while (result := self._command_result(command_id, deadline)) is None:
            self._wait()
        return result

    def _send(self, kind: str, **params: object) -> str:
        self._status()
        assert self.session is not None
        self.next_command += 1
        command_id = f"{self.run_id}-{self.next_command}"
        response = self.controller.command(command_id, kind, params, self.session)
        if response.id != command_id:
            raise ControllerError("Controlador respondeu com outro ID de comando.")
        return command_id

    def _command_result(self, command_id: str, deadline: float) -> dict[str, str] | None:
        self._status()
        response = self.controller.command_status(command_id)
        if response.id != command_id:
            raise ControllerError("Controlador respondeu com outro ID de comando.")
        if response.estado == "concluido":
            return response.resultado or {}
        if response.estado == "falhou":
            raise ControllerError(f"Comando {command_id} falhou: {response.erro}.")
        if response.estado not in ("aceito", "em_execucao") or monotonic() >= deadline:
            raise ControllerError(f"Estado inesperado ou tempo excedido no comando {command_id}.")
        return None

    def _status(self) -> ControllerStatus:
        if self.manager._stop.is_set():
            raise ControllerError("Servidor encerrou a execução.")
        status = self.controller.status()
        if self.session is not None and status.sessao_id != self.session:
            raise ControllerError("Sessão do controlador mudou. Reconcilie a maquete.")
        if status.falhas:
            raise ControllerError(f"Falha no controlador: {status.falhas}.")
        return status

    def _wait(self) -> None:
        self.manager._stop.wait(self.manager.poll_interval)
