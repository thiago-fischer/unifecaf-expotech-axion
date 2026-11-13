from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.planning_schema import PlanRequest, Positive

Station = Literal["M1", "M2", "M3"]


class ExecutionRequest(BaseModel):
    planning: PlanRequest = Field(default_factory=PlanRequest)
    machine_mapping: dict[Positive, Station] = Field(min_length=1, max_length=3)


class ExecutionStatus(BaseModel):
    id: str
    order_id: int
    state: Literal["queued", "running", "completed", "interrupted"]
    completed_operations: list[str] = Field(default_factory=list)
    approved_units: list[str] = Field(default_factory=list)
    unit_rfids: dict[str, str] = Field(default_factory=dict)
    reason: str | None = None
