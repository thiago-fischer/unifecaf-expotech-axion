import logging
from os import environ
from threading import Event
from time import monotonic
from urllib.error import URLError
from urllib.request import Request, urlopen

from pydantic import BaseModel

from .schemas import CommandStatus, ControllerStatus
from .simulator import Simulator

logger = logging.getLogger(__name__)


class ControllerEvent(BaseModel):
    status: ControllerStatus
    resultados: list[CommandStatus]


def publish_events(controller: Simulator, url: str, stop: Event) -> None:
    headers = {"Content-Type": "application/json"}
    token = environ.get("AXION_CONTROLLER_EVENTS_TOKEN")
    if token:
        headers["X-Axion-Event-Token"] = token
    previous = None
    pending: list[CommandStatus] = []
    session = None
    retry_at = 0.0
    while not stop.is_set():
        status, finished = controller.event_snapshot()
        if session != status.sessao_id:
            pending.clear()
            session = status.sessao_id
        pending.extend(finished)
        signature = (
            session,
            status.velocidade,
            status.comandos_ativos,
            status.leitura_rfid,
        )
        if (signature != previous or pending) and monotonic() >= retry_at:
            batch = pending[:100]
            request = Request(
                url,
                data=ControllerEvent(status=status, resultados=batch).model_dump_json().encode(),
                headers=headers,
            )
            try:
                with urlopen(request, timeout=2) as response:
                    if response.status == 204:
                        previous = signature
                        del pending[: len(batch)]
                    else:
                        retry_at = monotonic() + 1
            except (URLError, OSError) as exc:
                logger.warning("Entrega de evento pendente: %s", exc)
                retry_at = monotonic() + 1
        stop.wait(0.025)
