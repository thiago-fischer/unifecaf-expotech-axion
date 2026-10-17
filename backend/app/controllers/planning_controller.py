import logging
from typing import Annotated

from axion_optimizer.domain import PlanningLimitsError
from fastapi import APIRouter, Depends, HTTPException, Path, Request
from fastapi.responses import JSONResponse
from pydantic import BeforeValidator

from app.schemas.order_schema import OrderNotFoundResponse
from app.schemas.planning_schema import (
    OptimalityNotProven,
    PlanningBusy,
    PlanningLimits,
    PlanRequest,
    PlanResponse,
)
from app.schemas.product_schema import InvalidInputResponse
from app.services.order_service import OrderNotFoundError
from app.services.planning_service import PlanningBusyError, PlanningService

router = APIRouter(prefix="/orders", tags=["planning"])
logger = logging.getLogger(__name__)


def integer_path(value: object) -> object:
    if isinstance(value, str) and not value.isdecimal():
        raise ValueError("O ID deve representar um inteiro positivo.")
    return value


def get_planning_service(request: Request) -> PlanningService:
    return PlanningService(request.app.state.session_factory)


@router.post(
    "/{order_id}/plan",
    response_model=PlanResponse,
    responses={
        404: {"model": OrderNotFoundResponse},
        409: {"model": OptimalityNotProven},
        422: {"model": PlanningLimits | InvalidInputResponse},
        503: {"model": PlanningBusy, "headers": {"Retry-After": {"schema": {"type": "string"}}}},
        500: {"description": "Erro interno do servidor"},
    },
)
def plan_order(
    order_id: Annotated[int, Path(gt=0), BeforeValidator(integer_path)],
    data: PlanRequest,
    service: Annotated[PlanningService, Depends(get_planning_service)],
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
