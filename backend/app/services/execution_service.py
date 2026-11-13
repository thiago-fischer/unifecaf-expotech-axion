import logging
from collections import deque
from dataclasses import dataclass
from threading import Event, Lock, Thread
from time import monotonic
from uuid import uuid4

from app.schemas.execution_schema import ExecutionStatus, Station
from app.schemas.planning_schema import PlanOperation, PlanResponse
from app.services.controller_client import (
    CommandStatus,
    ControllerClient,
    ControllerError,
    ControllerEvent,
    ControllerStatus,
    SimulationSpeed,
)
from app.services.planning_service import build_machine_queues

logger = logging.getLogger(__name__)
BUFFERS = ("B1", "B2")
MIN_SIMULATION_SPEED = 0.5


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
        self._latest_id: str | None = None
        self._controller_lock = Lock()
        self._snapshot: ControllerStatus | None = None
        self._snapshot_at = 0.0
        self._retry_at = 0.0
        self._status_error: ControllerError | None = None
        self._retired_sessions: set[str] = set()
        self._results: dict[str, CommandStatus] = {}
        self._changed = Event()

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
            self._latest_id = run.id
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

    def snapshot(self) -> tuple[ControllerStatus, ExecutionStatus | None, float]:
        with self._lock:
            self.controller_status()
            with self._controller_lock:
                status = self._snapshot
                age_ms = max(0, (monotonic() - self._snapshot_at) * 1000)
            assert status is not None
            run = self._runs[self._latest_id] if self._latest_id else None
            return status, run.model_copy(deep=True) if run is not None else None, age_ms

    def _save_status(self, status: ControllerStatus) -> bool:
        if status.sessao_id in self._retired_sessions:
            return False
        if self._snapshot:
            if status.sessao_id != self._snapshot.sessao_id:
                self._retired_sessions.add(self._snapshot.sessao_id)
                self._results.clear()
            elif status.sequencia and status.sequencia <= self._snapshot.sequencia:
                return True
        self._snapshot = status
        self._snapshot_at = monotonic()
        self._status_error = None
        return True

    def controller_status(self, *, max_age: float = 10) -> ControllerStatus:
        with self._controller_lock:
            now = monotonic()
            if self._status_error is not None and now < self._retry_at:
                raise self._status_error
            if self._snapshot is None or now - self._snapshot_at >= max_age:
                try:
                    if not self._save_status(self.controller.status()):
                        raise ControllerError("O controlador respondeu com uma sessão anterior.")
                except ControllerError as exc:
                    self._status_error = exc
                    self._retry_at = monotonic() + 2
                    raise
            assert self._snapshot is not None
            return self._snapshot

    def accept_event(self, event: ControllerEvent) -> None:
        with self._controller_lock:
            if self._save_status(event.status):
                for result in event.resultados:
                    if result.estado in ("concluido", "falhou"):
                        self._results[result.id] = result
                # Reenvios e comandos manuais também podem chegar fora de uma OP.
                while len(self._results) > 1100:
                    del self._results[next(iter(self._results))]
                self._changed.set()

    def take_result(self, command_id: str) -> CommandStatus | None:
        with self._controller_lock:
            return self._results.pop(command_id, None)

    def set_speed(self, speed: SimulationSpeed) -> None:
        with self._controller_lock:
            self.controller.set_simulation_speed(speed)
            self._snapshot_at = float("-inf")

    def reset_simulation(self) -> None:
        with self._lock:
            run = self._runs[self._latest_id] if self._latest_id else None
            if self._stop.is_set() or (run is not None and run.state in ("queued", "running")):
                raise ExecutionBusy
            with self._controller_lock:
                self.controller.reset_simulation()
                if self._snapshot:
                    self._retired_sessions.add(self._snapshot.sessao_id)
                self._snapshot = None
                self._results.clear()
                self._status_error = None
            self._latest_id = None

    def close(self) -> None:
        with self._lock:
            self._stop.set()
            self._changed.set()
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
        self.recover_at: dict[str, float] = {}
        self.sent_at: dict[str, float] = {}

    def run(self) -> None:
        try:
            with self.manager._lock:
                self.manager._runs[self.run_id].state = "running"
            self._initialize()
            while self.units:
                self._finish_processing()
                status = self._status()
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
        status = self._status(max_age=0)
        self.session = status.sessao_id
        if (
            status.mesa.com_peca
            or status.mesa.movimento is not None
            or status.mesa.cabecote != "recolhido"
            or any(
                status.ocupacao.get(station) is not False
                for station in ("M1", "M2", "M3", "QA", *BUFFERS)
            )
        ):
            raise ControllerError("A execução requer mesa e estações livres no início.")

        counts: dict[str, int] = {}
        for queue in self.queues.values():
            for op in queue:
                counts[op.unit_id] = counts.get(op.unit_id, 0) + 1
        warehouse = sum(
            slot.startswith("ARMAZEM_") and occupied for slot, occupied in status.ocupacao.items()
        )
        output = sum(
            slot.startswith("ESTOQUE_FINAL_") and not occupied
            for slot, occupied in status.ocupacao.items()
        )
        if warehouse < len(counts) or output < len(counts):
            raise ControllerError("Peças no armazém ou vagas no estoque final insuficientes.")
        self.units = {unit_id: Unit("ARMAZEM", count) for unit_id, count in counts.items()}
        if not status.mesa.referenciada:
            self._table("referenciar_mesa")

    def _dispatch(self, status: ControllerStatus) -> bool:
        if status.ocupacao.get("QA") is False:
            for unit_id, unit in self.units.items():
                if unit.remaining == 0:
                    self._review(unit_id, unit)
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
            return self._buffer_finished_piece(status)
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
            command_id, monotonic() + operation.duration_seconds / MIN_SIMULATION_SPEED + 10
        )
        return True

    def _buffer_finished_piece(self, status: ControllerStatus) -> bool:
        destination = next((slot for slot in BUFFERS if status.ocupacao.get(slot) is False), None)
        if destination is None:
            return False
        for unit in self.units.values():
            if unit.position in self.queues and unit.position not in self.processing:
                self._table("coletar_peca", origem=unit.position)
                self._table("depositar_peca", destino=destination)
                unit.position = destination
                return True
        return False

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

    def _review(self, unit_id: str, unit: Unit) -> None:
        self._table("coletar_peca", origem=unit.position)
        self._table("depositar_peca", destino="QA")
        read = self._read("QA")
        approved = read == unit.rfid
        self._table("coletar_peca", origem="QA")
        self._table(
            "depositar_peca",
            destino="ESTOQUE_FINAL",
            resultado_qa="aprovada" if approved else "rejeitada",
        )
        del self.units[unit_id]
        with self.manager._lock:
            run = self.manager._runs[self.run_id]
            if approved:
                run.approved_units.append(unit_id)
            else:
                run.rejected_units[unit_id] = f"RFID divergente no QA: {read}."

    def _read(self, point: str) -> str:
        result = self._table("ler_rfid", ponto=point)
        if not result.get("rfid"):
            raise ControllerError("Controlador concluiu a leitura sem RFID.")
        return result["rfid"]

    def _table(self, kind: str, **params: object) -> dict[str, str]:
        command_id = self._send(kind, **params)
        deadline = monotonic() + 10 / MIN_SIMULATION_SPEED
        while (result := self._command_result(command_id, deadline)) is None:
            self._wait()
        return result

    def _send(self, kind: str, **params: object) -> str:
        self._status()
        assert self.session is not None
        self.next_command += 1
        command_id = f"{self.run_id}-{self.next_command}"
        started = monotonic()
        response = self.controller.command(command_id, kind, params, self.session)
        logger.debug(
            "Admissão de %s (%s) em %.1f ms", command_id, kind, (monotonic() - started) * 1000
        )
        if response.id != command_id:
            raise ControllerError("Controlador respondeu com outro ID de comando.")
        self.recover_at[command_id] = monotonic() + self.recovery_interval
        self.sent_at[command_id] = started
        return command_id

    def _command_result(self, command_id: str, deadline: float) -> dict[str, str] | None:
        status = self._status()
        now = monotonic()
        response = self.manager.take_result(command_id)
        if response is None:
            if now < min(self.recover_at[command_id], deadline):
                return None
            station = next(
                (
                    name
                    for name, active in self.processing.items()
                    if active.command_id == command_id
                ),
                None,
            )
            if station and command_id in status.comandos_ativos and now < deadline:
                machine = status.maquinas.get(station)
                if machine and machine.tempo_restante_ms:
                    with self.manager._controller_lock:
                        elapsed = (now - self.manager._snapshot_at) * status.velocidade
                    if machine.tempo_restante_ms > elapsed * 1000:
                        self.recover_at[command_id] = now + self.recovery_interval
                        return None
            self.recover_at[command_id] = now + self.recovery_interval
            logger.debug("Consultando recuperação do comando %s", command_id)
            response = self.controller.command_status(command_id)
            if response.estado == "concluido":
                self._status(max_age=0)
        if response.id != command_id:
            raise ControllerError("Controlador respondeu com outro ID de comando.")
        if response.estado == "concluido":
            self.recover_at.pop(command_id, None)
            logger.debug(
                "Conclusão de %s em %.1f ms",
                command_id,
                (monotonic() - self.sent_at.pop(command_id)) * 1000,
            )
            return response.resultado or {}
        if response.estado == "falhou":
            raise ControllerError(f"Comando {command_id} falhou: {response.erro}.")
        if response.estado not in ("aceito", "em_execucao") or monotonic() >= deadline:
            raise ControllerError(f"Estado inesperado ou tempo excedido no comando {command_id}.")
        return None

    def _status(self, *, max_age: float = 10) -> ControllerStatus:
        if self.manager._stop.is_set():
            raise ControllerError("Servidor encerrou a execução.")
        status = self.manager.controller_status(max_age=max_age)
        self.recovery_interval = 2 if status.sequencia else self.manager.poll_interval
        if self.session is not None and status.sessao_id != self.session:
            raise ControllerError("Sessão do controlador mudou. Reconcilie a maquete.")
        if status.falhas:
            raise ControllerError(f"Falha no controlador: {status.falhas}.")
        return status

    def _wait(self) -> None:
        self.manager._changed.wait(self.manager.poll_interval)
        self.manager._changed.clear()
