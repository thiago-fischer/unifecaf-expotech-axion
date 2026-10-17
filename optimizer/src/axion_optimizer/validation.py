import json
from collections import defaultdict
from dataclasses import asdict
from typing import Any

from axion_optimizer.domain import PlanningError, Problem, Reservation


def require(condition: bool, rule: str) -> None:
    if not condition:
        raise PlanningError(rule)


def validate_plan(problem: Problem, plan: tuple[Reservation, ...]) -> int:
    expected = {o.operation_id: o for o in problem.operations}
    actual = {r.operation_id: r for r in plan}
    require(
        len(plan) == len(actual) == len(expected) and actual.keys() == expected.keys(),
        "Cobertura exata de operações",
    )
    machines: dict[int, list[Reservation]] = defaultdict(list)
    units: dict[str, list[Reservation]] = defaultdict(list)
    for reservation in plan:
        operation = expected[reservation.operation_id]
        require(
            type(reservation.start_seconds) is int and type(reservation.end_seconds) is int,
            "Tempos inteiros",
        )
        require(
            reservation.start_seconds >= 0 and reservation.end_seconds <= problem.horizon,
            "Horizonte e tempo não negativo",
        )
        require(
            reservation.end_seconds - reservation.start_seconds == operation.duration_seconds,
            "Duração da receita",
        )
        predecessor = operation.predecessor_operation_id
        require(
            predecessor is None or reservation.start_seconds >= actual[predecessor].end_seconds,
            "Precedência da unidade",
        )
        machines[operation.machine_id].append(reservation)
        units[operation.unit_id].append(reservation)
    for agenda in [*machines.values(), *units.values()]:
        agenda.sort(key=lambda r: r.start_seconds)
        require(
            all(a.end_seconds <= b.start_seconds for a, b in zip(agenda, agenda[1:], strict=False)),
            "Sobreposição de recurso ou unidade",
        )
    return max(r.end_seconds for r in plan)


def validate_result(problem: Problem, result: dict[str, Any]) -> None:
    """Check serialized identities, schedules, metrics and proof independently."""
    require(
        json.loads(json.dumps(result["input_snapshot"]))
        == json.loads(json.dumps(asdict(problem.snapshot))),
        "Snapshot serializado",
    )
    rows = result["operations"]
    plan = tuple(Reservation(r["operation_id"], r["start_seconds"], r["end_seconds"]) for r in rows)
    upper = validate_plan(problem, plan)
    by_id = {r.operation_id: r for r in plan}
    expected = {o.operation_id: o for o in problem.operations}
    for row in rows:
        operation = expected[row["operation_id"]]
        for field in (
            "unit_id",
            "unit_index",
            "product_id",
            "step_sequence",
            "machine_id",
            "duration_seconds",
            "predecessor_operation_id",
        ):
            require(
                type(row[field]) is type(getattr(operation, field))
                and row[field] == getattr(operation, field),
                f"Identidade/duração: {field}",
            )
        predecessor = operation.predecessor_operation_id
        ready = by_id[predecessor].end_seconds if predecessor else 0
        require(row["waiting_seconds"] == row["start_seconds"] - ready, "Espera")

    def key(row: dict[str, Any]) -> tuple[int, ...]:
        return (
            row["start_seconds"],
            row["machine_id"],
            row["product_id"],
            row["unit_index"],
            row["step_sequence"],
        )

    require(rows == sorted(rows, key=key), "Ordenação do cronograma")
    metrics = result["metrics"]
    lower = metrics["lower_bound_seconds"]
    require(type(lower) is int and problem.analytical_bound <= lower <= upper, "Limites")
    require(metrics["makespan_seconds"] == metrics["upper_bound_seconds"] == upper, "Makespan")
    require(
        metrics["unit_count"] == problem.unit_count and metrics["operation_count"] == len(expected),
        "Contagens",
    )
    require(
        metrics["absolute_gap_seconds"] == upper - lower
        and metrics["relative_gap_percent"] == round(100 * (upper - lower) / upper, 2),
        "Gap",
    )
    baselines = result["search"]["baseline_results"]
    baseline = min(baselines, key=lambda b: b["makespan_seconds"])
    require(
        metrics["baseline_name"] == baseline["name"]
        and metrics["baseline_makespan_seconds"] == baseline["makespan_seconds"]
        and upper <= baseline["makespan_seconds"],
        "Referência oficial",
    )
    require(
        metrics["improvement_percent"]
        == round(100 * (baseline["makespan_seconds"] - upper) / baseline["makespan_seconds"], 2),
        "Melhoria",
    )
    proven = lower == upper
    require(
        result["optimality_proven"] is proven
        and result["quality"] == ("optimal" if proven else "feasible"),
        "Qualidade",
    )
    proof = result["proof"]
    require(proof["lower_bound_seconds"] == lower, "Limite da prova")
    certification = result["search"]["certification"]
    certified_lower = certification.get("lower_bound_seconds")
    if certified_lower is None:
        # Compatibility with the documentary example, whose OPTIMAL status is illustrative.
        certified_lower = (
            certification["candidate_makespan_seconds"]
            if certification["solver_status"] == "OPTIMAL"
            else 0
        )
    require(
        type(certified_lower) is int
        and 0 <= certified_lower <= upper
        and lower == max(problem.analytical_bound, certified_lower),
        "Evidência do limite",
    )
    require(
        proof["solver_status"] == certification["solver_status"]
        and proof["solver_version"] == certification["solver_version"],
        "Proveniência da prova",
    )
    if proof["method"] == "analytical_bound":
        require(proven and problem.analytical_bound == upper, "Prova analítica")
    elif proof["method"] == "cp_sat":
        require(
            proven
            and certified_lower == upper
            and certification["solver_status"] in {"OPTIMAL", "FEASIBLE", "UNKNOWN"}
            and certification["absolute_gap_limit"] == 0
            and certification["relative_gap_limit"] == 0,
            "Prova CP-SAT",
        )
    else:
        require(proof["method"] == "none" and not proven, "Ausência de prova")
    ga = result["search"]["ga"]
    require(
        upper
        <= ga["best_makespan_seconds"]
        <= ga["initial_best_makespan_seconds"]
        <= baseline["makespan_seconds"],
        "Elitismo e origem",
    )
    source = result["selected_source"]
    candidate = certification["candidate_makespan_seconds"]
    require(
        (
            source == "genetic_algorithm"
            and upper == ga["best_makespan_seconds"]
            and (candidate is None or candidate >= upper)
        )
        or (source == "cp_sat" and upper == candidate < ga["best_makespan_seconds"]),
        "Origem do cronograma",
    )
    require(result["execution_ready"] is False, "Execução física não autorizada")
    machine_metrics = result["machine_metrics"]
    require(
        [m["machine_id"] for m in machine_metrics]
        == [m.machine_id for m in problem.snapshot.machines],
        "Cobertura de métricas",
    )
    for machine in machine_metrics:
        busy = sum(
            o.duration_seconds for o in expected.values() if o.machine_id == machine["machine_id"]
        )
        require(
            machine["busy_seconds"] == busy
            and machine["idle_seconds"] == upper - busy
            and machine["utilization_percent"] == round(100 * busy / upper, 2),
            "Métricas de máquina",
        )
