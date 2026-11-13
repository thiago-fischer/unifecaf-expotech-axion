from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from os import environ
from threading import Event, Thread
from typing import Annotated

from fastapi import FastAPI, Header, Request, Response
from fastapi.responses import JSONResponse

from .events import publish_events
from .schemas import (
    CommandRequest,
    CommandStatus,
    ControllerStatus,
    ErrorResponse,
    MachineStatus,
    SpeedRequest,
)
from .simulator import ControllerError, Simulator


def create_app(simulator: Simulator | None = None) -> FastAPI:
    controller = (
        simulator
        if simulator is not None
        else Simulator(initial_pieces=int(environ.get("AXION_CONTROLLER_INITIAL_PIECES", "1")))
    )

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        url = environ.get("AXION_CONTROLLER_EVENTS_URL")
        stop = Event()
        worker = Thread(target=publish_events, args=(controller, url, stop)) if url else None
        if worker:
            worker.start()
        try:
            yield
        finally:
            stop.set()
            if worker:
                worker.join()

    app = FastAPI(title="Axion — Controlador simulado", version="0.1.0", lifespan=lifespan)

    @app.exception_handler(ControllerError)
    async def handle_controller_error(_request: Request, error: ControllerError) -> JSONResponse:
        return JSONResponse(
            status_code=error.status_code,
            content=ErrorResponse(detail=error.detail).model_dump(),
        )

    @app.post(
        "/api/comandos",
        status_code=202,
        response_model_exclude_none=True,
        responses={
            200: {"model": CommandStatus, "description": "Comando já registrado"},
            404: {"model": ErrorResponse},
            409: {"model": ErrorResponse},
        },
    )
    def submit(
        command: CommandRequest,
        response: Response,
        expected_session: Annotated[str | None, Header(alias="X-Axion-Session")] = None,
    ) -> CommandStatus:
        status, created = controller.submit(command, expected_session=expected_session)
        if not created:
            response.status_code = 200
        return status

    @app.get(
        "/api/comandos/{id}",
        response_model_exclude_none=True,
        responses={404: {"model": ErrorResponse}},
    )
    def command_status(id: str) -> CommandStatus:
        return controller.command_status(id)

    @app.get("/api/status")
    def status() -> ControllerStatus:
        return controller.status()

    @app.post("/api/simulacao/reset", status_code=204)
    def reset_simulation() -> Response:
        controller.reset()
        return Response(status_code=204)

    @app.post("/api/simulacao/velocidade", status_code=204)
    def set_simulation_speed(data: SpeedRequest) -> Response:
        controller.set_speed(data.velocidade)
        return Response(status_code=204)

    @app.get("/api/maquinas/{id}/status", responses={404: {"model": ErrorResponse}})
    def machine_status(id: str) -> MachineStatus:
        return controller.machine_status(id)

    return app
