from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.machine_schema import MachineName

PositiveInteger = Annotated[int, Field(strict=True, gt=0)]


class ProductStepCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sequence: PositiveInteger
    machine_id: PositiveInteger
    processing_time_seconds: PositiveInteger


class ProductCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: MachineName
    steps: Annotated[list[ProductStepCreate], Field(min_length=1, strict=True)]


class ProductStepRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sequence: int
    machine_id: int
    processing_time_seconds: int


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(gt=0)
    name: str
    steps: list[ProductStepRead]


class ProductNotFoundResponse(BaseModel):
    detail: str = "Produto não encontrado."


class MissingMachinesResponse(BaseModel):
    detail: str = "Uma ou mais máquinas das etapas não existem."
    machine_ids: list[int]


class InvalidRecipeResponse(BaseModel):
    detail: str


class InvalidInputResponse(BaseModel):
    detail: list[dict[str, object]]
