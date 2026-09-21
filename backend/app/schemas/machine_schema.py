from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

MachineName = Annotated[
    str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=100)
]


class MachineCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: MachineName


class MachineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(gt=0)
    name: str


class MachineNotFoundResponse(BaseModel):
    detail: str = "Máquina não encontrada."
