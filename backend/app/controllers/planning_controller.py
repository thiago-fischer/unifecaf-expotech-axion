import logging
from os import environ
from secrets import compare_digest
from typing import Annotated

from axion_optimizer.domain import PlanningLimitsError
from fastapi import APIRouter, Depends, Header, HTTPException, Path, Request
from fastapi.responses import JSONResponse
from pydantic import BeforeValidator

from app.schemas.execution_schema import ExecutionRequest, ExecutionStatus, SimulationSpeedRequest
from app.schemas.order_schema import OrderNotFoundResponse
from app.schemas.planning_schema import (
    MachineQueues,
    OptimalityNotProven,
    PlanningBusy,
    PlanningLimits,
    PlanRequest,
    PlanResponse,
)
from app.schemas.product_schema import InvalidInputResponse
from app.services.controller_client import ControllerError, ControllerEvent, ControllerStatus
from app.services.execution_service import ExecutionBusy, ExecutionManager, InvalidExecution
from app.services.order_service import OrderNotFoundError
from app.services.planning_service import PlanningBusyError, PlanningService, build_machine_queues

router = APIRouter(tags=["planning"])
logger = logging.getLogger(__name__)
PLAN_ERRORS = {
    404: {"model": OrderNotFoundResponse},
    409: {"model": OptimalityNotProven},
    422: {"model": PlanningLimits | InvalidInputResponse},
    503: {"model": PlanningBusy, "headers": {"Retry-After": {"schema": {"type": "string"}}}},
    500: {"description": "Erro interno do servidor"},
}


def integer_path(value: object) -> object:
    if isinstance(value, str) and not value.isdecimal():
        raise ValueError("O ID deve representar um inteiro positivo.")
    return value


def get_planning_service(request: Request) -> PlanningService:
    return PlanningService(request.app.state.session_factory)


def get_execution_manager(request: Request) -> ExecutionManager:
    return request.app.state.execution_manager


@router.post(
    "/orders/{order_id}/plan",
    response_model=PlanResponse,
    responses=PLAN_ERRORS,
)
def plan_order(
    order_id: Annotated[int, Path(gt=0), BeforeValidator(integer_path)],
    data: PlanRequest,
    service: Annotated[PlanningService, Depends(get_planning_service)],
) -> PlanResponse | JSONResponse:
    return _plan(order_id, data, service)


@router.post("/orders/{order_id}/plan/queues", response_model=MachineQueues, responses=PLAN_ERRORS)
def plan_machine_queues(
    order_id: Annotated[int, Path(gt=0), BeforeValidator(integer_path)],
    data: PlanRequest,
    service: Annotated[PlanningService, Depends(get_planning_service)],
) -> MachineQueues | JSONResponse:
    result = _plan(order_id, data, service)
    if isinstance(result, JSONResponse):
        return result
    return build_machine_queues(result)


@router.post(
    "/orders/{order_id}/executions",
    status_code=202,
    response_model=ExecutionStatus,
    responses={**PLAN_ERRORS, 409: {"description": "Execução ativa ou ótimo sem comprovação"}},
)
def start_execution(
    order_id: Annotated[int, Path(gt=0), BeforeValidator(integer_path)],
    data: ExecutionRequest,
    service: Annotated[PlanningService, Depends(get_planning_service)],
    manager: Annotated[ExecutionManager, Depends(get_execution_manager)],
) -> ExecutionStatus | JSONResponse:
    result = _plan(order_id, data.planning, service)
    if isinstance(result, JSONResponse):
        return result
    try:
        return manager.start(result, data.machine_mapping)
    except ExecutionBusy as exc:
        raise HTTPException(409, detail="Já existe uma execução ativa.") from exc
    except InvalidExecution as exc:
        raise HTTPException(422, detail=str(exc)) from exc


@router.get("/orders/{order_id}/executions/{execution_id}", response_model=ExecutionStatus)
def execution_status(
    order_id: Annotated[int, Path(gt=0), BeforeValidator(integer_path)],
    execution_id: str,
    manager: Annotated[ExecutionManager, Depends(get_execution_manager)],
) -> ExecutionStatus:
    status = manager.status(execution_id)
    if status is None or status.order_id != order_id:
        raise HTTPException(404, detail="Execução não encontrada.")
    return status


class SimulationStatus(ControllerStatus):
    execution: ExecutionStatus | None
    idade_ms: float


@router.post("/controller/events", status_code=204)
def receive_controller_event(
    event: ControllerEvent,
    manager: Annotated[ExecutionManager, Depends(get_execution_manager)],
    token: Annotated[str, Header(alias="X-Axion-Event-Token")] = "",
) -> None:
    expected = environ.get("AXION_CONTROLLER_EVENTS_TOKEN", "")
    if expected and not compare_digest(token.encode(), expected.encode()):
        raise HTTPException(403, detail="Evento do controlador não autorizado.")
    manager.accept_event(event)


@router.get("/simulation/status", response_model=SimulationStatus)
def simulation_status(
    manager: Annotated[ExecutionManager, Depends(get_execution_manager)],
) -> SimulationStatus:
    try:
        status, execution, age_ms = manager.snapshot()
    except ControllerError as exc:
        raise HTTPException(503, detail=str(exc)) from exc
    return SimulationStatus(**status.model_dump(), execution=execution, idade_ms=age_ms)


@router.post("/simulation/reset", status_code=204)
def reset_simulation(
    manager: Annotated[ExecutionManager, Depends(get_execution_manager)],
) -> None:
    try:
        manager.reset_simulation()
    except ExecutionBusy as exc:
        raise HTTPException(
            409, detail="Aguarde a execução terminar para restaurar a maquete."
        ) from exc
    except ControllerError as exc:
        raise HTTPException(503, detail=str(exc)) from exc


@router.post("/simulation/speed", status_code=204)
def set_simulation_speed(
    data: SimulationSpeedRequest,
    manager: Annotated[ExecutionManager, Depends(get_execution_manager)],
) -> None:
    try:
        manager.controller.set_simulation_speed(data.velocidade)
    except ControllerError as exc:
        raise HTTPException(503, detail=str(exc)) from exc


def _plan(
    order_id: int, data: PlanRequest, service: PlanningService
) -> PlanResponse | JSONResponse:
    try:
        result = service.plan(order_id, data)
    except OrderNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Ordem de produção não encontrada.") from exc
    except PlanningLimitsError as exc:
        return JSONResponse(
            status_code=422, content=PlanningLimits(violations=exc.violations).model_dump()
        )
    except PlanningBusyError:
        return JSONResponse(
            status_code=503, content=PlanningBusy().model_dump(), headers={"Retry-After": "1"}
        )
    except Exception:
        logger.exception("Falha no planejamento da ordem %s", order_id)
        return JSONResponse(status_code=500, content={"detail": "Erro interno do servidor."})
    if data.optimality_policy == "require_proof" and not result.optimality_proven:
        return JSONResponse(
            status_code=409, content=OptimalityNotProven(result=result).model_dump()
        )
    return result
