from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.product_schema import PositiveInteger


class OrderItemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_id: PositiveInteger
    quantity: PositiveInteger


class OrderCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: Annotated[list[OrderItemCreate], Field(min_length=1, strict=True)]


class OrderItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: int
    quantity: int


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(gt=0)
    items: list[OrderItemRead]


class OrderNotFoundResponse(BaseModel):
    detail: str = "Ordem de produção não encontrada."


class MissingProductsResponse(BaseModel):
    detail: str = "Um ou mais produtos da ordem não existem."
    product_ids: list[int]


class DuplicateProductResponse(BaseModel):
    detail: str = "Cada produto pode aparecer somente uma vez na ordem."
