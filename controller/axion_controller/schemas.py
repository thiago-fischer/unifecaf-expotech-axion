from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

Identifier = Annotated[str, Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")]
MachineID = Literal["M1", "M2", "M3", "QA"]
ReadingPoint = Literal["LEITOR_RFID", "QA"]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Command(Input):
    id: Identifier


class Empty(Input):
    pass


class Reference(Command):
    tipo: Literal["referenciar_mesa"]
    parametros: Empty = Field(default_factory=Empty)


class Destination(Input):
    destino: Identifier


class Move(Command):
    tipo: Literal["mover_para"]
    parametros: Destination


class CollectParams(Input):
    origem: Identifier


class Collect(Command):
    tipo: Literal["coletar_peca"]
    parametros: CollectParams


class Deposit(Command):
    tipo: Literal["depositar_peca"]
    parametros: Destination


class ReadParams(Input):
    ponto: ReadingPoint


class ReadRFID(Command):
    tipo: Literal["ler_rfid"]
    parametros: ReadParams


class ProcessParams(Input):
    maquina_id: Literal["M1", "M2", "M3"]
    duracao_ms: Annotated[int, Field(ge=1, le=2_147_483_647)]


class Process(Command):
    tipo: Literal["iniciar_processamento"]
    parametros: ProcessParams


CommandRequest = Annotated[
    Reference | Move | Collect | Deposit | ReadRFID | Process,
    Field(discriminator="tipo"),
]


class ErrorInfo(BaseModel):
    codigo: str
    mensagem: str


class ErrorResponse(BaseModel):
    detail: ErrorInfo


class CommandStatus(BaseModel):
    id: str
    estado: Literal["aceito", "em_execucao", "concluido", "falhou"]
    resultado: dict[str, str] | None = None
    erro: ErrorInfo | None = None


class MachineStatus(BaseModel):
    id: MachineID
    estado: Literal["livre", "pronta", "processando", "aguardando_retirada", "em_revisao"]
    ocupada: bool
    tempo_restante_ms: int | None = None


class Movement(BaseModel):
    origem: str | None
    destino: str
    progresso: float


class TableStatus(BaseModel):
    referenciada: bool
    posicao: str | None
    movimento: Movement | None
    cabecote: Literal["recolhido", "manipulando"]
    com_peca: bool


class ControllerStatus(BaseModel):
    sessao_id: str
    mesa: TableStatus
    maquinas: dict[MachineID, MachineStatus]
    ocupacao: dict[str, bool]
    falhas: list[ErrorInfo]
