import json
from copy import deepcopy
from itertools import permutations, product
from pathlib import Path
from random import Random

import pytest

from axion_optimizer import planner
from axion_optimizer.certification import Certification, certify
from axion_optimizer.decoder import decode, makespan, priority
from axion_optimizer.domain import (
    Item,
    Machine,
    PlanningError,
    PlanningLimitsError,
    Reservation,
    Snapshot,
    Step,
    prepare,
)
from axion_optimizer.genetic_algorithm import GAResult, crossover, mutate, run_ga
from axion_optimizer.validation import validate_plan, validate_result


def snapshot(routes: list[list[tuple[int, int]]], quantities: list[int] | None = None) -> Snapshot:
    quantities = quantities or [1] * len(routes)
    return Snapshot(
        tuple(
            Item(
                10 + 7 * i,
                "Nome repetido",
                quantities[i],
                tuple(Step(j, m, d) for j, (m, d) in enumerate(route, 1)),
            )
            for i, route in enumerate(routes)
        ),
        tuple(Machine(m, "Máquina repetida") for m in sorted({m for r in routes for m, _ in r})),
    )


def oracle(data: Snapshot) -> int:
    """Enumerate MACHINE orders, then longest paths in each acyclic precedence graph."""
    problem = prepare(data)
    operations = {o.operation_id: o for o in problem.operations}
    groups = [
        [o.operation_id for o in operations.values() if o.machine_id == m.machine_id]
        for m in data.machines
    ]
    optimum = problem.horizon
    for orders in product(*(permutations(group) for group in groups)):
        predecessors = {oid: set() for oid in operations}
        for oid, operation in operations.items():
            if operation.predecessor_operation_id:
                predecessors[oid].add(operation.predecessor_operation_id)
        for order in orders:
            for a, b in zip(order, order[1:], strict=False):
                predecessors[b].add(a)
        ends: dict[str, int] = {}
        while len(ends) < len(operations):
            eligible = [
                oid for oid, deps in predecessors.items() if oid not in ends and deps <= ends.keys()
            ]
            if not eligible:
                break  # A cycle rules out this set of machine orders.
            for oid in eligible:
                ends[oid] = (
                    max((ends[p] for p in predecessors[oid]), default=0)
                    + operations[oid].duration_seconds
                )
        if len(ends) == len(operations):
            optimum = min(optimum, max(ends.values()))
    return optimum


@pytest.mark.parametrize(
    "routes,quantities,expected",
    [
        ([[(7, 10)], [(99, 10)]], [1, 1], 10),
        ([[(7, 10)], [(7, 10)]], [1, 1], 20),
        ([[(7, 10), (99, 10)]], [2], 30),
        ([[(7, 3), (99, 2), (7, 4)], [(99, 5)]], [1, 1], 10),
        ([[(7, 3), (7, 2)]], [2], 10),
    ],
)
def test_real_planning(
    routes: list[list[tuple[int, int]]], quantities: list[int], expected: int
) -> None:
    data = snapshot(routes, quantities)
    result = planner.plan(data, 81, ga_time_limit_seconds=1, certification_time_limit_seconds=1)
    assert result["metrics"]["makespan_seconds"] == expected == oracle(data)
    assert result["quality"] == "optimal"
    assert result["execution_ready"] is False
    validate_result(prepare(data), result)


def test_gap_insertion() -> None:
    problem = prepare(snapshot([[(7, 10), (99, 5)], [(99, 5)]]))
    schedule = decode(problem, priority(problem))
    assert schedule[-1] == Reservation("p17-u1-s1", 0, 5)
    assert makespan(schedule) == 15


def test_eight_operation_oracle() -> None:
    data = snapshot([[(7, 3), (99, 2), (123, 2)], [(7, 2), (123, 1), (99, 4)], [(99, 4), (123, 3)]])
    assert oracle(data) == 11
    assert planner.plan(data, 1)["metrics"]["makespan_seconds"] == 11


@pytest.mark.parametrize("seed", range(10))
def test_operators_generated_invariants_and_oracle(seed: int) -> None:
    rng = Random(seed)
    routes = [
        [(rng.choice([7, 99, 123]), rng.randint(1, 10)) for _ in range(rng.randint(1, 3))]
        for _ in range(2)
    ]
    data = snapshot(routes, [2 if sum(map(len, routes)) <= 4 else 1, 1])
    problem = prepare(data)
    assert len(problem.operations) <= 8
    chromosome = priority(problem)
    other = tuple(rng.sample(chromosome, len(chromosome)))
    for _ in range(20):
        other = mutate(crossover(chromosome, other, rng), rng)
        assert sorted(other) == sorted(chromosome)
        validate_plan(problem, decode(problem, other))
    state = __import__("random").getstate()
    ga = run_ga(problem, seed, None, generation_limit=5)
    again = run_ga(problem, seed, None, generation_limit=5)
    assert __import__("random").getstate() == state
    assert ga.plan == again.plan
    for field in ["evaluations", "initial_best_makespan_seconds", "best_makespan_seconds"]:
        assert ga.metadata[field] == again.metadata[field]
    best = validate_plan(problem, ga.plan)
    exact = oracle(data)
    assert problem.analytical_bound <= exact <= best <= min(v for _, v in ga.baselines)
    certificate = certify(problem, ga.plan, seed, 2)
    assert certificate.status == "OPTIMAL"
    assert validate_plan(problem, certificate.plan) == exact
    assert certificate.lower_bound == exact


def test_single_operation_and_small_search_space() -> None:
    problem = prepare(snapshot([[(100, 7)]]))
    ga = run_ga(problem, 0, None)
    assert ga.metadata["termination_reason"] == "trivial_instance"
    assert ga.metadata["evaluations"] == 1
    assert ga.metadata["population_size"] == 40
    assert crossover(("a",), ("a",), Random(0)) == ("a",)
    assert mutate(("a",), Random(0)) == ("a",)


def historical(quantities: list[int]) -> Snapshot:
    return snapshot(
        [[(1, 10), (3, 15)], [(2, 15), (3, 20)], [(1, 10), (2, 15), (3, 20)]], quantities
    )


@pytest.mark.parametrize("quantities,expected", [([1, 1, 1], 65), ([3, 2, 4], 175)])
def test_historical(quantities: list[int], expected: int) -> None:
    result = planner.plan(
        historical(quantities), 7, ga_time_limit_seconds=1, certification_time_limit_seconds=2
    )
    assert result["metrics"]["makespan_seconds"] == expected
    assert result["optimality_proven"]


@pytest.mark.parametrize(
    "status", ["OPTIMAL", "FEASIBLE", "UNKNOWN", "INFEASIBLE", "MODEL_INVALID"]
)
def test_controlled_solver_status(monkeypatch: pytest.MonkeyPatch, status: str) -> None:
    problem = prepare(historical([1, 1, 1]))
    ga = run_ga(problem, 0, None, generation_limit=0)
    monkeypatch.setattr(planner, "run_ga", lambda *args: ga)
    candidate = None if status == "UNKNOWN" else ga.plan
    monkeypatch.setattr(
        planner,
        "certify",
        lambda *args: Certification(
            status, candidate, makespan(ga.plan) if status == "OPTIMAL" else 55, 0.0
        ),
    )
    if status in {"INFEASIBLE", "MODEL_INVALID"}:
        with pytest.raises(PlanningError, match="Estado inesperado"):
            planner.plan_problem(problem, 1)
    else:
        result = planner.plan_problem(problem, 1)
        assert result["quality"] == ("optimal" if status == "OPTIMAL" else "feasible")
        assert result["selected_source"] == "genetic_algorithm"


def test_cp_improvement_and_tie(monkeypatch: pytest.MonkeyPatch) -> None:
    problem = prepare(historical([1, 1, 1]))
    ga = run_ga(problem, 0, None, generation_limit=0)
    # A controlled, valid GA incumbent made sequential (baseline adjusted to same reference).
    time = 0
    sequential = []
    for operation in problem.operations:
        sequential.append(
            Reservation(operation.operation_id, time, time + operation.duration_seconds)
        )
        time += operation.duration_seconds
    metadata = {**ga.metadata, "initial_best_makespan_seconds": time, "best_makespan_seconds": time}
    controlled = GAResult(
        tuple(sequential), (("canonical_priority", time), ("spt", time)), metadata
    )
    monkeypatch.setattr(planner, "run_ga", lambda *args: controlled)
    result = planner.plan_problem(problem, 1, certification_time_limit_seconds=2)
    assert result["selected_source"] == "cp_sat"
    assert result["metrics"]["makespan_seconds"] == 65 < time
    monkeypatch.setattr(planner, "run_ga", lambda *args: ga)
    result = planner.plan_problem(problem, 1)
    assert result["selected_source"] == "genetic_algorithm"


def test_bound_proof_without_optimal_status(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        planner,
        "certify",
        lambda p, hint, *args: Certification("FEASIBLE", hint, makespan(hint), 0),
    )
    result = planner.plan(historical([1, 1, 1]), 1)
    assert result["proof"]["method"] == "cp_sat"
    monkeypatch.setattr(planner, "certify", lambda *args: Certification("UNKNOWN", None, 0, 0))
    result = planner.plan(snapshot([[(7, 10)]]), 1)
    assert result["proof"]["method"] == "analytical_bound"


def test_gap_rounding_does_not_prove(monkeypatch: pytest.MonkeyPatch) -> None:
    data = snapshot(
        [
            [(1, 10_000_000), (3, 15_000_000)],
            [(2, 15_000_000), (3, 20_000_000)],
            [(1, 10_000_000), (2, 15_000_000), (3, 20_000_000)],
        ]
    )
    monkeypatch.setattr(
        planner,
        "certify",
        lambda p, hint, *args: Certification("FEASIBLE", hint, makespan(hint) - 1, 0),
    )
    result = planner.plan(data, 1)
    assert result["metrics"]["relative_gap_percent"] == 0.0
    assert result["metrics"]["absolute_gap_seconds"] == 1
    assert result["quality"] == "feasible"


@pytest.mark.parametrize(
    "change",
    [
        "missing",
        "duplicate",
        "machine",
        "duration",
        "overlap",
        "precedence",
        "float",
        "waiting",
        "makespan",
        "gap",
        "utilization",
        "proof",
        "snapshot",
    ],
)
def test_validator_rejects_tampering(change: str) -> None:
    data = historical([1, 1, 1])
    result = deepcopy(
        planner.plan(data, 1, ga_time_limit_seconds=1, certification_time_limit_seconds=1)
    )
    row = result["operations"][0]
    if change == "missing":
        result["operations"].pop()
    elif change == "duplicate":
        result["operations"].append(deepcopy(row))
    elif change == "machine":
        row["machine_id"] = 999
    elif change == "duration":
        row["duration_seconds"] += 1
    elif change == "overlap":
        target = next(r for r in result["operations"][1:] if r["machine_id"] == row["machine_id"])
        target["start_seconds"] = 0
        target["end_seconds"] = target["duration_seconds"]
    elif change == "precedence":
        target = next(r for r in result["operations"] if r["step_sequence"] == 2)
        target["start_seconds"] = 0
        target["end_seconds"] = target["duration_seconds"]
    elif change == "float":
        row["start_seconds"] = float(row["start_seconds"])
    elif change == "waiting":
        row["waiting_seconds"] += 1
    elif change == "makespan":
        result["metrics"]["makespan_seconds"] += 1
    elif change == "gap":
        result["metrics"]["absolute_gap_seconds"] += 1
    elif change == "utilization":
        result["machine_metrics"][0]["utilization_percent"] += 1
    elif change == "proof":
        result["proof"]["lower_bound_seconds"] -= 1
    elif change == "snapshot":
        result["input_snapshot"]["items"][0]["product_name"] = "Adulterado"
    with pytest.raises(PlanningError):
        validate_result(prepare(data), result)


def test_documentary_example() -> None:
    example = Path(__file__).resolve().parents[2] / "docs/examples/planning-response.json"
    result = json.loads(example.read_text(encoding="utf-8"))
    data = Snapshot(
        tuple(
            Item(
                i["product_id"],
                i["product_name"],
                i["quantity"],
                tuple(Step(**s) for s in i["steps"]),
            )
            for i in result["input_snapshot"]["items"]
        ),
        tuple(Machine(**m) for m in result["input_snapshot"]["machines"]),
    )
    validate_result(prepare(data), result)
    assert oracle(data) == 65


def test_limits_before_expansion_and_all_violations() -> None:
    data = snapshot([[(7, 1_000_000_001)] * 11], [10**12])
    with pytest.raises(PlanningLimitsError) as caught:
        prepare(data)
    assert [v["field"] for v in caught.value.violations] == [
        "horizon_seconds",
        "operation_count",
        "unit_count",
    ]
    assert prepare(snapshot([[(7, 1)] * 10], [100])).unit_count == 100
    assert len(prepare(snapshot([[(7, 1)] * 10], [100])).operations) == 1000
    assert prepare(snapshot([[(7, 1_000_000_000)]])).horizon == 1_000_000_000
    assert len(prepare(snapshot([[(i, 1) for i in range(1, 51)]])).snapshot.machines) == 50
    with pytest.raises(PlanningLimitsError) as caught:
        prepare(snapshot([[(i, 1) for i in range(1, 52)]]))
    assert caught.value.violations[0]["field"] == "machine_count"


@pytest.mark.parametrize(
    "data",
    [
        Snapshot((), ()),
        snapshot([[]]),
        snapshot([[(7, 0)]]),
        snapshot([[(7, True)]]),
        snapshot([[(7, 1)]], [True]),
        Snapshot(snapshot([[(7, 1)]]).items, (Machine(99, "Ausente"),)),
    ],
)
def test_inconsistent_snapshot(data: Snapshot) -> None:
    with pytest.raises(PlanningError):
        prepare(data)


def test_deadline_retains_best(monkeypatch: pytest.MonkeyPatch) -> None:
    from axion_optimizer import genetic_algorithm

    clock = iter([0.0, 0.0, 0.0, 2.0, 2.0, 2.0, 2.0])
    monkeypatch.setattr(genetic_algorithm, "monotonic", lambda: next(clock, 2.0))
    problem = prepare(historical([1, 1, 1]))
    ga = run_ga(problem, 0, 1)
    assert ga.metadata["termination_reason"] == "time_limit"
    assert ga.metadata["completed_generations"] == 0
    assert makespan(ga.plan) <= min(v for _, v in ga.baselines)


def test_solver_failure_propagates(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*args: object) -> None:
        raise RuntimeError("controlled failure")

    monkeypatch.setattr(planner, "certify", fail)
    with pytest.raises(RuntimeError):
        planner.plan(historical([1, 1, 1]), 1)
