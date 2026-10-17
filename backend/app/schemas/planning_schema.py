from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PlanningSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class PlanRequest(PlanningSchema):
    optimality_policy: Literal["require_proof", "allow_feasible"] = "require_proof"
    ga_time_limit_seconds: Annotated[int, Field(ge=1, le=20)] = 3
    certification_time_limit_seconds: Annotated[int, Field(ge=1, le=20)] = 7
    seed: Annotated[int, Field(ge=0, le=2_147_483_647)] = 0

    @model_validator(mode="after")
    def total_budget(self) -> PlanRequest:
        if self.ga_time_limit_seconds + self.certification_time_limit_seconds > 30:
            raise ValueError("A soma dos orçamentos deve ser de até 30 segundos.")
        return self


class Assumptions(PlanningSchema):
    all_units_released_at_zero: Literal[True]
    all_machines_available_at_zero: Literal[True]
    machine_capacity: Literal[1]
    nonpreemptive_operations: Literal[True]
    deterministic_durations: Literal[True]
    unlimited_buffers: Literal[True]
    transport_time_seconds: Literal[0]
    setup_time_seconds: Literal[0]
    shared_transport_resource_modeled: Literal[False]
    machine_blocking_modeled: Literal[False]


Positive = Annotated[int, Field(gt=0)]
Nonnegative = Annotated[int, Field(ge=0)]
Elapsed = Annotated[float, Field(ge=0, allow_inf_nan=False)]
Percent = Annotated[float, Field(ge=0, le=100, allow_inf_nan=False)]
SolverStatus = Literal["OPTIMAL", "FEASIBLE", "UNKNOWN"]


class SnapshotStep(PlanningSchema):
    sequence: Positive
    machine_id: Positive
    processing_time_seconds: Positive


class SnapshotItem(PlanningSchema):
    product_id: Positive
    product_name: str
    quantity: Positive
    steps: list[SnapshotStep]


class SnapshotMachine(PlanningSchema):
    machine_id: Positive
    machine_name: str


class InputSnapshot(PlanningSchema):
    items: list[SnapshotItem]
    machines: list[SnapshotMachine]


class PlanMetrics(PlanningSchema):
    makespan_seconds: Positive
    unit_count: Positive
    operation_count: Positive
    lower_bound_seconds: Positive
    upper_bound_seconds: Positive
    absolute_gap_seconds: Nonnegative
    relative_gap_percent: Percent
    baseline_name: Literal["canonical_priority", "spt"]
    baseline_makespan_seconds: Positive
    improvement_percent: Percent


class BaselineResult(PlanningSchema):
    name: Literal["canonical_priority", "spt"]
    makespan_seconds: Positive


class GeneticSearch(PlanningSchema):
    profile: Literal["ga_v1"]
    time_limit_seconds: Positive
    population_size: Positive
    generation_limit: Positive
    tournament_size: Positive
    crossover_probability: float
    mutation_probability_per_child: float
    elite_count: Positive
    initial_best_makespan_seconds: Positive
    best_makespan_seconds: Positive
    completed_generations: Nonnegative
    evaluations: Positive
    elapsed_seconds: Elapsed
    termination_reason: Literal["generation_limit", "time_limit", "trivial_instance"]


class CertificationSearch(PlanningSchema):
    lower_bound_seconds: Nonnegative | None = None
    time_limit_seconds: Positive
    elapsed_seconds: Elapsed
    solver_status: SolverStatus
    solver_version: str
    seed: Nonnegative
    num_search_workers: Literal[1]
    absolute_gap_limit: Literal[0]
    relative_gap_limit: Literal[0]
    candidate_makespan_seconds: Positive | None


class PlanSearch(PlanningSchema):
    planner_version: str
    seed: Nonnegative
    baseline_results: list[BaselineResult]
    preparation_seconds: Elapsed
    total_planning_seconds: Elapsed
    ga: GeneticSearch
    certification: CertificationSearch


class PlanProof(PlanningSchema):
    method: Literal["cp_sat", "analytical_bound", "none"]
    solver_version: str
    solver_status: SolverStatus
    lower_bound_seconds: Positive


class PlanOperation(PlanningSchema):
    operation_id: str
    unit_id: str
    unit_index: Positive
    product_id: Positive
    step_sequence: Positive
    machine_id: Positive
    start_seconds: Nonnegative
    end_seconds: Positive
    duration_seconds: Positive
    predecessor_operation_id: str | None
    waiting_seconds: Nonnegative


class MachineMetrics(PlanningSchema):
    machine_id: Positive
    busy_seconds: Positive
    idle_seconds: Nonnegative
    utilization_percent: Percent


class PlanResponse(PlanningSchema):
    schema_version: Literal[1]
    order_id: Positive
    model_version: Literal["job_shop_v1"]
    time_unit: Literal["seconds"]
    quality: Literal["optimal", "feasible"]
    optimality_proven: bool
    selected_source: Literal["genetic_algorithm", "cp_sat"]
    execution_ready: Literal[False]
    assumptions: Assumptions
    input_snapshot: InputSnapshot
    metrics: PlanMetrics
    search: PlanSearch
    proof: PlanProof
    operations: list[PlanOperation]
    machine_metrics: list[MachineMetrics]


class OptimalityNotProven(PlanningSchema):
    code: Literal["optimality_not_proven"] = "optimality_not_proven"
    result: PlanResponse


class PlanningBusy(PlanningSchema):
    code: Literal["planning_busy"] = "planning_busy"
    detail: str = "Planejamento temporariamente ocupado."


class LimitViolation(PlanningSchema):
    field: str
    actual: int
    limit: int


class PlanningLimits(PlanningSchema):
    code: Literal["planning_limits_exceeded"] = "planning_limits_exceeded"
    detail: str = "A ordem excede os limites de planejamento."
    violations: list[LimitViolation]
