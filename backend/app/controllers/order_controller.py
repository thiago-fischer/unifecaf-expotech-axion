from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database.database import get_session
from app.models.production_order import ProductionOrder
from app.schemas.order_schema import (
    DuplicateProductResponse,
    MissingProductsResponse,
    OrderCreate,
    OrderNotFoundResponse,
    OrderRead,
)
from app.schemas.product_schema import InvalidInputResponse
from app.services.order_service import (
    DuplicateProductError,
    MissingProductsError,
    OrderNotFoundError,
    OrderService,
)

router = APIRouter(prefix="/orders", tags=["orders"])


def get_order_service(session: Annotated[Session, Depends(get_session)]) -> OrderService:
    return OrderService(session)


Service = Annotated[OrderService, Depends(get_order_service)]


@router.post(
    "",
    response_model=OrderRead,
    status_code=status.HTTP_201_CREATED,
    responses={
        422: {
            "description": "Entrada, duplicidade ou referências a produtos inválidas",
            "model": MissingProductsResponse | DuplicateProductResponse | InvalidInputResponse,
        }
    },
)
def create_order(data: OrderCreate, service: Service) -> ProductionOrder | JSONResponse:
    try:
        return service.create(data)
    except DuplicateProductError:
        return JSONResponse(status_code=422, content=DuplicateProductResponse().model_dump())
    except MissingProductsError as exc:
        return JSONResponse(
            status_code=422,
            content=MissingProductsResponse(product_ids=exc.product_ids).model_dump(),
        )


@router.get("", response_model=list[OrderRead])
def list_orders(service: Service) -> list[ProductionOrder]:
    return service.list_all()


@router.get(
    "/{order_id}",
    response_model=OrderRead,
    responses={404: {"model": OrderNotFoundResponse}},
)
def get_order(order_id: Annotated[int, Path(gt=0)], service: Service) -> ProductionOrder:
    try:
        return service.get(order_id)
    except OrderNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Ordem de produção não encontrada.") from exc
