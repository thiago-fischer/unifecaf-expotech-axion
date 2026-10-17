from dataclasses import asdict
from time import monotonic
from typing import Any

from axion_optimizer import __version__
from axion_optimizer.certification import certify
from axion_optimizer.decoder import makespan
from axion_optimizer.domain import PlanningError, Problem, Snapshot, prepare
from axion_optimizer.genetic_algorithm import run_ga
from axion_optimizer.validation import require, validate_plan, validate_result

ASSUMPTIONS = dict(
    all_units_released_at_zero=True,
    all_machines_available_at_zero=True,
    machine_capacity=1,
    nonpreemptive_operations=True,
    deterministic_durations=True,
    unlimited_buffers=True,
    transport_time_seconds=0,
    setup_time_seconds=0,
    shared_transport_resource_modeled=False,
    machine_blocking_modeled=False,
)


def plan(
    snapshot: Snapshot,
    order_id: int,
    seed: int = 0,
    ga_time_limit_seconds: int = 3,
    certification_time_limit_seconds: int = 7,
) -> dict[str, Any]:
    start = monotonic()
    problem = prepare(snapshot)
    return plan_problem(
        problem,
        order_id,
        seed,
        ga_time_limit_seconds,
        certification_time_limit_seconds,
        started_at=start,
    )


def plan_problem(
    problem: Problem,
    order_id: int,
    seed: int = 0,
    ga_time_limit_seconds: int = 3,
    certification_time_limit_seconds: int = 7,
    *,
    started_at: float | None = None,
) -> dict[str, Any]:
    start = monotonic() if started_at is None else started_at
    preparation = monotonic() - start
    ga = run_ga(problem, seed, ga_time_limit_seconds)
    ga_upper = validate_plan(problem, ga.plan)
    certificate = certify(problem, ga.plan, seed, certification_time_limit_seconds)
    if certificate.status not in {"OPTIMAL", "FEASIBLE", "UNKNOWN"}:
        raise PlanningError(f"Estado inesperado do solver: {certificate.status}")
    selected = ga.plan
    source = "genetic_algorithm"
    candidate_upper = None
    if certificate.plan is not None:
        candidate_upper = validate_plan(problem, certificate.plan)
        require(candidate_upper <= ga_upper, "Candidato viola limite superior do AG")
        if candidate_upper < ga_upper:
            selected, source = certificate.plan, "cp_sat"
    require(
        (certificate.plan is not None) == (certificate.status != "UNKNOWN"),
        "Estado e candidato inconsistentes",
    )
    upper = makespan(selected)
    require(
        type(certificate.lower_bound) is int and 0 <= certificate.lower_bound <= upper,
        "Limite certificado inconsistente",
    )
    lower = max(problem.analytical_bound, certificate.lower_bound)
    if certificate.status == "OPTIMAL":
        require(
            candidate_upper == upper and certificate.lower_bound == upper,
            "OPTIMAL sem evidência exata",
        )
    proven = lower == upper
    method = "none"
    if proven:
        method = "cp_sat" if certificate.lower_bound == upper else "analytical_bound"
    baseline_name, baseline_upper = min(ga.baselines, key=lambda pair: pair[1])
    ends = {r.operation_id: r.end_seconds for r in selected}
    operations = {o.operation_id: o for o in problem.operations}
    rows = []
    for reservation in selected:
        operation = operations[reservation.operation_id]
        ready = ends.get(operation.predecessor_operation_id, 0)
        rows.append(
            dict(
                **asdict(operation),
                start_seconds=reservation.start_seconds,
                end_seconds=reservation.end_seconds,
                waiting_seconds=reservation.start_seconds - ready,
            )
        )
    rows.sort(
        key=lambda r: (
            r["start_seconds"],
            r["machine_id"],
            r["product_id"],
            r["unit_index"],
            r["step_sequence"],
        )
    )
    machine_metrics = []
    for machine in problem.snapshot.machines:
        busy = sum(
            o.duration_seconds for o in problem.operations if o.machine_id == machine.machine_id
        )
        machine_metrics.append(
            dict(
                machine_id=machine.machine_id,
                busy_seconds=busy,
                idle_seconds=upper - busy,
                utilization_percent=round(100 * busy / upper, 2),
            )
        )
    result = dict(
        schema_version=1,
        order_id=order_id,
        model_version="job_shop_v1",
        time_unit="seconds",
        quality="optimal" if proven else "feasible",
        optimality_proven=proven,
        selected_source=source,
        execution_ready=False,
        assumptions=dict(ASSUMPTIONS),
        input_snapshot=asdict(problem.snapshot),
        metrics=dict(
            makespan_seconds=upper,
            unit_count=problem.unit_count,
            operation_count=len(problem.operations),
            lower_bound_seconds=lower,
            upper_bound_seconds=upper,
            absolute_gap_seconds=upper - lower,
            relative_gap_percent=round(100 * (upper - lower) / upper, 2),
            baseline_name=baseline_name,
            baseline_makespan_seconds=baseline_upper,
            improvement_percent=round(100 * (baseline_upper - upper) / baseline_upper, 2),
        ),
        search=dict(
            planner_version=__version__,
            seed=seed,
            baseline_results=[
                dict(name=name, makespan_seconds=value) for name, value in ga.baselines
            ],
            preparation_seconds=preparation,
            total_planning_seconds=0.0,
            ga=ga.metadata,
            certification=dict(
                lower_bound_seconds=certificate.lower_bound,
                time_limit_seconds=certification_time_limit_seconds,
                elapsed_seconds=certificate.elapsed_seconds,
                solver_status=certificate.status,
                solver_version=certificate.solver_version,
                seed=seed,
                num_search_workers=1,
                absolute_gap_limit=0,
                relative_gap_limit=0,
                candidate_makespan_seconds=candidate_upper,
            ),
        ),
        proof=dict(
            method=method,
            solver_version=certificate.solver_version,
            solver_status=certificate.status,
            lower_bound_seconds=lower,
        ),
        operations=rows,
        machine_metrics=machine_metrics,
    )
    validate_result(problem, result)
    result["search"]["total_planning_seconds"] = monotonic() - start
    return result
