from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database.database import get_session
from app.models.product import Product
from app.schemas.product_schema import (
    InvalidInputResponse,
    InvalidRecipeResponse,
    MissingMachinesResponse,
    ProductCreate,
    ProductNotFoundResponse,
    ProductRead,
)
from app.services.product_service import (
    InvalidSequenceError,
    MissingMachinesError,
    ProductNotFoundError,
    ProductService,
)

router = APIRouter(prefix="/products", tags=["products"])


def get_product_service(session: Annotated[Session, Depends(get_session)]) -> ProductService:
    return ProductService(session)


Service = Annotated[ProductService, Depends(get_product_service)]


@router.post(
    "",
    response_model=ProductRead,
    status_code=status.HTTP_201_CREATED,
    responses={
        422: {
            "description": "Entrada, sequência ou referências a máquinas inválidas",
            "model": MissingMachinesResponse | InvalidRecipeResponse | InvalidInputResponse,
        }
    },
)
def create_product(data: ProductCreate, service: Service) -> Product | JSONResponse:
    try:
        return service.create(data)
    except InvalidSequenceError as exc:
        raise HTTPException(
            status_code=422,
            detail="As sequências das etapas devem ser únicas e consecutivas, de 1 a N.",
        ) from exc
    except MissingMachinesError as exc:
        return JSONResponse(
            status_code=422,
            content=MissingMachinesResponse(machine_ids=exc.machine_ids).model_dump(),
        )


@router.get("", response_model=list[ProductRead])
def list_products(service: Service) -> list[Product]:
    return service.list_all()


@router.get(
    "/{product_id}",
    response_model=ProductRead,
    responses={404: {"model": ProductNotFoundResponse}},
)
def get_product(product_id: Annotated[int, Path(gt=0)], service: Service) -> Product:
    try:
        return service.get(product_id)
    except ProductNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Produto não encontrado.") from exc
