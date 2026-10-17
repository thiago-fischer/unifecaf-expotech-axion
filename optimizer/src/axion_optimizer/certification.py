from dataclasses import dataclass
from math import floor, isfinite
from time import monotonic

import ortools
from ortools.sat.python import cp_model

from axion_optimizer.decoder import makespan
from axion_optimizer.domain import PlanningError, Problem, Reservation


@dataclass(frozen=True)
class Certification:
    status: str
    plan: tuple[Reservation, ...] | None
    lower_bound: int
    elapsed_seconds: float
    solver_version: str = ortools.__version__


def certify(
    problem: Problem, hint: tuple[Reservation, ...], seed: int, time_limit: int
) -> Certification:
    start = monotonic()
    model = cp_model.CpModel()
    starts, ends = {}, {}
    # Sparse external IDs map to dense internal resource indices.
    machine_index = {m.machine_id: i for i, m in enumerate(problem.snapshot.machines)}
    intervals: list[list[cp_model.IntervalVar]] = [[] for _ in machine_index]
    upper = makespan(hint)
    for operation in problem.operations:
        oid = operation.operation_id
        starts[oid] = model.new_int_var(0, problem.horizon, f"s_{oid}")
        ends[oid] = model.new_int_var(0, problem.horizon, f"e_{oid}")
        intervals[machine_index[operation.machine_id]].append(
            model.new_interval_var(starts[oid], operation.duration_seconds, ends[oid], oid)
        )
    for operation in problem.operations:
        if operation.predecessor_operation_id is not None:
            model.add(starts[operation.operation_id] >= ends[operation.predecessor_operation_id])
    for agenda in intervals:
        model.add_no_overlap(agenda)
    objective = model.new_int_var(problem.analytical_bound, upper, "makespan")
    model.add_max_equality(objective, list(ends.values()))
    model.minimize(objective)
    for reservation in hint:
        model.add_hint(starts[reservation.operation_id], reservation.start_seconds)
        model.add_hint(ends[reservation.operation_id], reservation.end_seconds)
    model.add_hint(objective, upper)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = seed
    solver.parameters.absolute_gap_limit = 0
    solver.parameters.relative_gap_limit = 0
    status = solver.status_name(solver.solve(model))
    bound = solver.best_objective_bound
    if not isfinite(bound):
        raise PlanningError("Limite não finito do solver")
    plan = None
    if status in {"OPTIMAL", "FEASIBLE"}:
        plan = tuple(
            Reservation(
                o.operation_id,
                solver.value(starts[o.operation_id]),
                solver.value(ends[o.operation_id]),
            )
            for o in problem.operations
        )
    return Certification(status, plan, max(0, floor(bound)), monotonic() - start)
