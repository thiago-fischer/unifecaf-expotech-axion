from os import environ
from typing import Annotated

from fastapi import FastAPI, Header, Request, Response
from fastapi.responses import JSONResponse

from .schemas import CommandRequest, CommandStatus, ControllerStatus, ErrorResponse, MachineStatus
from .simulator import ControllerError, Simulator


def create_app(simulator: Simulator | None = None) -> FastAPI:
    controller = (
        simulator
        if simulator is not None
        else Simulator(initial_pieces=int(environ.get("AXION_CONTROLLER_INITIAL_PIECES", "1")))
    )
    app = FastAPI(title="Axion — Controlador simulado", version="0.1.0")

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

    @app.get("/api/maquinas/{id}/status", responses={404: {"model": ErrorResponse}})
    def machine_status(id: str) -> MachineStatus:
        return controller.machine_status(id)

    return app
