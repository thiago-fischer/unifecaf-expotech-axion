import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import BaseModel, Field, ValidationError


class ControllerError(Exception):
    pass


class Table(BaseModel):
    referenciada: bool
    com_peca: bool
    movimento: dict[str, object] | None
    cabecote: str
    posicao: str | None = None
    progresso_cabecote: float = 0


class Machine(BaseModel):
    estado: str
    tempo_restante_ms: int | None


class ControllerStatus(BaseModel):
    sessao_id: str
    mesa: Table
    ocupacao: dict[str, bool]
    falhas: list[dict[str, object]]
    maquinas: dict[str, Machine] = Field(default_factory=dict)
    pecas: dict[str, str] = Field(default_factory=dict)
    rfid_transportado: str | None = None
    resultados_qa: dict[str, str] = Field(default_factory=dict)
    leitura_rfid: str | None = None


class CommandStatus(BaseModel):
    id: str
    estado: str
    resultado: dict[str, str] | None = None
    erro: dict[str, str] | None = None


class ControllerClient:
    def __init__(self, url: str) -> None:
        self.url = url.rstrip("/")

    def status(self) -> ControllerStatus:
        return self._request(ControllerStatus, "/api/status")

    def command(
        self, command_id: str, kind: str, params: dict[str, object], session: str
    ) -> CommandStatus:
        body = {"id": command_id, "tipo": kind, "parametros": params}
        return self._request(CommandStatus, "/api/comandos", body, session)

    def command_status(self, command_id: str) -> CommandStatus:
        return self._request(CommandStatus, f"/api/comandos/{command_id}")

    def _request[Model: BaseModel](
        self,
        model: type[Model],
        path: str,
        body: dict[str, object] | None = None,
        session: str | None = None,
    ) -> Model:
        headers = {"Accept": "application/json"}
        if session is not None:
            headers["X-Axion-Session"] = session
            headers["Content-Type"] = "application/json"
        request = Request(
            self.url + path,
            data=json.dumps(body).encode() if body is not None else None,
            headers=headers,
        )
        try:
            with urlopen(request, timeout=2) as response:
                return model.model_validate_json(response.read())
        except HTTPError as exc:
            try:
                detail = json.load(exc).get("detail")
                code = detail.get("codigo") if isinstance(detail, dict) else None
            except (ValueError, AttributeError, OSError):
                code = None
            finally:
                exc.close()
            raise ControllerError(f"Controlador recusou {path} (HTTP {exc.code}, {code}).") from exc
        except (URLError, OSError) as exc:
            raise ControllerError("Comunicação com o controlador interrompida.") from exc
        except ValidationError as exc:
            raise ControllerError(f"Resposta inválida do controlador em {path}.") from exc
