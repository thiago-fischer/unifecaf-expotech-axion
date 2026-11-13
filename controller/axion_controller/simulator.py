from collections.abc import Callable
from dataclasses import dataclass
from math import ceil
from threading import Lock
from time import monotonic
from typing import Literal, NoReturn
from uuid import uuid4

from .schemas import (
    Collect,
    CommandRequest,
    CommandStatus,
    ControllerStatus,
    Deposit,
    ErrorInfo,
    MachineID,
    MachineStatus,
    Move,
    Movement,
    Process,
    ReadRFID,
    Reference,
    TableStatus,
)

PROCESSING = ("M1", "M2", "M3")
MACHINES: tuple[MachineID, ...] = ("M1", "M2", "M3", "QA")
WAREHOUSE = tuple(f"ARMAZEM_{index:02}" for index in range(1, 11))
OUTPUT = tuple(f"ESTOQUE_FINAL_{index:02}" for index in range(1, 11))
HOME = "REFERENCIA"
READER = "LEITOR_RFID"
BUFFERS = ("B1", "B2")
SLOTS = (*WAREHOUSE, *BUFFERS, *MACHINES, *OUTPUT)
AXIS = (HOME, "ARMAZEM", *BUFFERS, READER, *MACHINES, "ESTOQUE_FINAL")


def axis_position(slot: str) -> str:
    if slot in WAREHOUSE:
        return "ARMAZEM"
    if slot in OUTPUT:
        return "ESTOQUE_FINAL"
    return slot


class ControllerError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.detail = ErrorInfo(codigo=code, mensagem=message)


@dataclass
class Execution:
    command: CommandRequest
    started: float
    ends: float
    target: str | None = None
    arrives: float | None = None
    completed: bool = False
    rfid: str | None = None
    slot: str | None = None

    def status(self) -> CommandStatus:
        return CommandStatus(
            id=self.command.id,
            estado="concluido" if self.completed else "em_execucao",
            resultado={"rfid": self.rfid} if self.rfid is not None else None,
        )


class Simulator:
    def __init__(self, initial_pieces: int, clock: Callable[[], float] = monotonic) -> None:
        if not 0 <= initial_pieces <= len(WAREHOUSE):
            raise ValueError("A quantidade inicial deve estar entre 0 e 10.")
        self._clock = clock
        self._lock = Lock()
        self._session_id = str(uuid4())
        self._position: str | None = None
        self._carried: str | None = None
        self._pieces = {
            slot: f"SIM-{index:03}"
            for index, slot in enumerate(WAREHOUSE[:initial_pieces], start=1)
        }
        self._processed: set[str] = set()
        self._quality: dict[str, Literal["aprovada", "rejeitada"]] = {}
        self._last_read: tuple[float, str] | None = None
        self._commands: dict[str, Execution] = {}
        self._table: Execution | None = None
        self._processing: dict[str, Execution] = {}

    def submit(
        self, command: CommandRequest, *, expected_session: str | None = None
    ) -> tuple[CommandStatus, bool]:
        with self._lock:
            if expected_session is not None and expected_session != self._session_id:
                self._conflict("sessao_alterada", "A sessão do controlador mudou.")
            now = self._clock()
            self._advance(now)
            existing = self._commands.get(command.id)
            if existing is not None:
                if existing.command != command:
                    self._conflict("id_em_uso", "ID já associado a outro comando.")
                return existing.status(), False

            if isinstance(command, Process):
                machine = command.parametros.maquina_id
                if machine in self._processing:
                    self._conflict("maquina_ocupada", "A máquina já está processando.")
                continuing = command.parametros.continuar_na_maquina
                if machine not in self._pieces or continuing != (machine in self._processed):
                    self._conflict(
                        "maquina_sem_peca_pronta", "A peça não está pronta para a etapa."
                    )
                if self._table is not None and self._table.target == machine:
                    self._conflict("maquina_ocupada", "A mesa está operando nesta máquina.")
                execution = Execution(command, now, now + command.parametros.duracao_ms / 1000)
                self._processed.discard(machine)
                self._processing[machine] = execution
            else:
                execution = self._prepare_table(command, now)
                self._table = execution
            self._commands[command.id] = execution
            return CommandStatus(id=command.id, estado="aceito"), True

    def command_status(self, command_id: str) -> CommandStatus:
        with self._lock:
            self._advance(self._clock())
            execution = self._commands.get(command_id)
            if execution is None:
                raise ControllerError(404, "comando_desconhecido", "Comando inexistente.")
            return execution.status()

    def machine_status(self, machine: str) -> MachineStatus:
        with self._lock:
            now = self._clock()
            self._advance(now)
            if machine not in MACHINES:
                raise ControllerError(404, "maquina_desconhecida", "Máquina inexistente.")
            return self._machine_status(machine, now)

    def status(self) -> ControllerStatus:
        with self._lock:
            now = self._clock()
            self._advance(now)
            movement = None
            manipulating = False
            head_progress = 0.0
            position = self._position
            table = self._table
            if table is not None and table.target is not None and table.arrives is not None:
                if now < table.arrives:
                    movement = Movement(
                        origem=self._position,
                        destino=table.target,
                        progresso=(now - table.started) / (table.arrives - table.started),
                    )
                else:
                    manipulating = isinstance(table.command, Collect | Deposit)
                    if manipulating:
                        head_progress = (now - table.arrives) / (table.ends - table.arrives)
                    position = table.target
            return ControllerStatus(
                sessao_id=self._session_id,
                mesa=TableStatus(
                    referenciada=self._position is not None,
                    posicao=position,
                    movimento=movement,
                    cabecote="manipulando" if manipulating else "recolhido",
                    progresso_cabecote=head_progress,
                    com_peca=self._carried is not None,
                ),
                maquinas={machine: self._machine_status(machine, now) for machine in MACHINES},
                ocupacao={slot: slot in self._pieces for slot in SLOTS},
                pecas=self._pieces.copy(),
                rfid_transportado=self._carried,
                resultados_qa=self._quality.copy(),
                leitura_rfid=(
                    self._last_read[1]
                    if self._last_read and now - self._last_read[0] < 0.6
                    else None
                ),
                falhas=[],
            )

    def _machine_status(self, machine: MachineID, now: float) -> MachineStatus:
        occupied = machine in self._pieces
        running = self._processing.get(machine)
        remaining = None
        if running is not None:
            state = "processando"
            remaining = ceil((running.ends - now) * 1000)
        elif not occupied:
            state = "livre"
        elif machine == "QA":
            state = "em_revisao"
        elif machine in self._processed:
            state = "aguardando_retirada"
        else:
            state = "pronta"
        return MachineStatus(
            id=machine, estado=state, ocupada=occupied, tempo_restante_ms=remaining
        )

    def _prepare_table(
        self, command: Reference | Move | Collect | Deposit | ReadRFID, now: float
    ) -> Execution:
        if self._table is not None:
            self._conflict("mesa_ocupada", "A mesa já está executando outro comando.")
        if isinstance(command, Reference):
            if self._carried is not None:
                self._conflict("cabecote_ocupado", "A referência exige cabeçote vazio.")
            return Execution(command, now, now + 0.1, HOME, now + 0.1)
        if self._position is None:
            self._conflict("mesa_sem_referencia", "Referencie a mesa antes da operação.")
        if isinstance(command, ReadRFID):
            point = command.parametros.ponto
            rfid = self._pieces.get(point)
            if point == READER and self._position == READER:
                rfid = self._carried
            if rfid is None:
                self._conflict("sem_peca_no_leitor", "Não há peça no ponto de leitura.")
            return Execution(command, now, now + 0.05, rfid=rfid)

        target = (
            command.parametros.origem
            if isinstance(command, Collect)
            else (command.parametros.destino)
        )
        slot = target
        if isinstance(command, Collect) and target == "ARMAZEM":
            slot = next((name for name in WAREHOUSE if name in self._pieces), None)
            if slot is None:
                self._conflict("origem_vazia", "A esteira de entrada está vazia.")
        if isinstance(command, Deposit) and target == "ESTOQUE_FINAL":
            slot = next((name for name in OUTPUT if name not in self._pieces), None)
            if slot is None:
                self._conflict("destino_ocupado", "A esteira de saída está cheia.")
        target = axis_position(target)
        if target not in AXIS or (not isinstance(command, Move) and slot not in SLOTS):
            raise ControllerError(404, "posicao_desconhecida", "Posição inválida para o comando.")
        if isinstance(command, Collect):
            if self._carried is not None:
                self._conflict("cabecote_ocupado", "O cabeçote já carrega uma peça.")
            if slot not in self._pieces:
                self._conflict("origem_vazia", "A origem não contém peça.")
            if target in PROCESSING and target not in self._processed:
                self._conflict("peca_nao_disponivel", "A operação na máquina ainda não terminou.")
        if isinstance(command, Deposit):
            if self._carried is None:
                self._conflict("cabecote_vazio", "O cabeçote não carrega uma peça.")
            if slot in self._pieces:
                self._conflict("destino_ocupado", "O destino já contém uma peça.")
            if command.parametros.resultado_qa is not None and slot not in OUTPUT:
                self._conflict("destino_qa_invalido", "O resultado de QA pertence à saída.")

        travel = 0.12 * abs(AXIS.index(target) - AXIS.index(self._position))
        handling = 0.25 if isinstance(command, Collect | Deposit) else 0.0
        return Execution(command, now, now + travel + handling, target, now + travel, slot=slot)

    def _advance(self, now: float) -> None:
        for machine, operation in tuple(self._processing.items()):
            if now >= operation.ends:
                operation.completed = True
                self._processed.add(machine)
                del self._processing[machine]

        table = self._table
        if table is None or now < table.ends:
            return
        if table.target is not None:
            self._position = table.target
        if isinstance(table.command, Collect):
            assert table.slot is not None
            origin = table.slot
            self._carried = self._pieces.pop(origin)
            self._processed.discard(origin)
        elif isinstance(table.command, Deposit):
            assert self._carried is not None
            assert table.slot is not None
            self._pieces[table.slot] = self._carried
            quality = table.command.parametros.resultado_qa
            if quality is not None:
                self._quality[self._carried] = quality
            self._carried = None
        elif (
            isinstance(table.command, ReadRFID)
            and table.command.parametros.ponto == READER
            and table.rfid is not None
        ):
            self._last_read = (table.ends, table.rfid)
        table.completed = True
        self._table = None

    @staticmethod
    def _conflict(code: str, message: str) -> NoReturn:
        raise ControllerError(409, code, message)
