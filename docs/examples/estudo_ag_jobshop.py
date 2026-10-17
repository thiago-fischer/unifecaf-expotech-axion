"""Experimento fixo de escalonamento; não é um módulo de produção do Axion.

Execute a partir da raiz: python docs/examples/estudo_ag_jobshop.py
Requer somente a biblioteca padrão do Python, sem instalar dependências.
Imprime JSON em stdout e não grava arquivos. A população inicial é inteiramente
aleatória, sem incluir os baselines. As seeds são fixas; os tempos de execução
dependem do ambiente. As verificações de viabilidade usam assert (execute sem -O).

O modelo permite paralelismo entre máquinas, com todas as unidades disponíveis
em t=0, e não inclui transporte, preparação nem restrições de buffers.
Restaurado em 17/10/2026 a partir do histórico e do protótipo original preservado.
"""

from __future__ import annotations

import json
import platform
import random
from collections import Counter
from dataclasses import dataclass
from itertools import permutations
from statistics import mean
from time import perf_counter
from typing import TypedDict

CATALOG = {
    "E": [("Torno", 10), ("Centro", 15)],
    "P": [("Fresadora", 15), ("Centro", 20)],
    "S": [("Torno", 10), ("Fresadora", 15), ("Centro", 20)],
}
POPULATION_SIZE = 40
GENERATIONS = 80
TOURNAMENT_SIZE = 3
CROSSOVER_PROBABILITY = 0.8
MUTATION_PROBABILITY = 0.2
SEEDS = tuple(range(10))


@dataclass(frozen=True)
class Operation:
    id: int
    unit: str
    step: int
    machine: str
    duration: int


@dataclass(frozen=True)
class Scheduled:
    op: Operation
    start: int
    end: int


class GARun(TypedDict):
    seed: int
    initial_best: int
    best: int
    genome: tuple[int, ...]
    unique_evaluations: int
    elapsed_seconds: float


def operations(demand: dict[str, int]) -> tuple[list[Operation], dict[str, list[Operation]]]:
    ops: list[Operation] = []
    units: dict[str, list[Operation]] = {}
    for product, quantity in demand.items():
        for number in range(1, quantity + 1):
            unit = f"{product}{number}"
            units[unit] = []
            for step, (machine, duration) in enumerate(CATALOG[product]):
                op = Operation(len(ops), unit, step, machine, duration)
                ops.append(op)
                units[unit].append(op)
    return ops, units


def validate(
    schedule: list[Scheduled], ops: list[Operation], units: dict[str, list[Operation]]
) -> None:
    """Confere completude, unicidade, duração, precedência e ocupação das máquinas."""
    assert len(schedule) == len(ops)
    by_id = {s.op.id: s for s in schedule}
    assert set(by_id) == {op.id for op in ops}
    for scheduled in schedule:
        assert scheduled.start >= 0
        assert scheduled.end - scheduled.start == scheduled.op.duration
    for route in units.values():
        for previous, following in zip(route, route[1:], strict=False):
            assert by_id[previous.id].end <= by_id[following.id].start
    for machine in {op.machine for op in ops}:
        same = sorted((s for s in schedule if s.op.machine == machine), key=lambda s: s.start)
        for previous, following in zip(same, same[1:], strict=False):
            assert previous.end <= following.start


def decode(
    genome: tuple[int, ...],
    ops: list[Operation],
    units: dict[str, list[Operation]],
    spt: bool = False,
) -> list[Scheduled]:
    """Usa genes como prioridades; só escolhe a próxima operação de cada unidade.

    Habilitada significa que a predecessora já foi agendada, não necessariamente
    concluída em um relógio global. Cada operação entra ao fim de sua máquina.
    SPT prioriza duração e usa o índice estável da operação para desempatar.
    """
    assert sorted(genome) == list(range(len(ops)))
    ranks = {op_id: i for i, op_id in enumerate(genome)}
    next_step = dict.fromkeys(units, 0)
    unit_ready = dict.fromkeys(units, 0)
    machine_ready: dict[str, int] = {}
    schedule: list[Scheduled] = []
    while len(schedule) < len(ops):
        eligible = [
            route[next_step[unit]] for unit, route in units.items() if next_step[unit] < len(route)
        ]
        op = min(eligible, key=lambda x: (x.duration, x.id) if spt else (ranks[x.id],))
        start = max(unit_ready[op.unit], machine_ready.get(op.machine, 0))
        end = start + op.duration
        schedule.append(Scheduled(op, start, end))
        next_step[op.unit] += 1
        unit_ready[op.unit] = end
        machine_ready[op.machine] = end
    validate(schedule, ops, units)
    return schedule


def makespan(schedule: list[Scheduled]) -> int:
    return max((s.end for s in schedule), default=0)


def ox(parent1: tuple[int, ...], parent2: tuple[int, ...], rng: random.Random) -> tuple[int, ...]:
    """Order crossover: preserva um segmento e completa sem repetir operações."""
    n = len(parent1)
    if n < 2:
        return parent1
    left, right = sorted(rng.sample(range(n + 1), 2))
    child: list[int | None] = [None] * n
    child[left:right] = parent1[left:right]
    used = set(parent1[left:right])
    available = [parent2[i % n] for i in range(right, right + n) if parent2[i % n] not in used]
    blanks = [i % n for i in range(right, right + n) if child[i % n] is None]
    for index, value in zip(blanks, available, strict=True):
        child[index] = value
    result = tuple(value for value in child if value is not None)
    assert sorted(result) == list(range(n))
    return result


def swap_mutation(genome: tuple[int, ...], rng: random.Random) -> tuple[int, ...]:
    child = list(genome)
    if len(child) >= 2 and rng.random() < MUTATION_PROBABILITY:
        a, b = rng.sample(range(len(child)), 2)
        child[a], child[b] = child[b], child[a]
    return tuple(child)


def run_ga(ops: list[Operation], units: dict[str, list[Operation]], seed: int) -> GARun:
    started = perf_counter()
    rng = random.Random(seed)
    cache: dict[tuple[int, ...], int] = {}

    def fitness(genome: tuple[int, ...]) -> int:
        if genome not in cache:
            cache[genome] = makespan(decode(genome, ops, units))
        return cache[genome]

    population = [tuple(rng.sample(range(len(ops)), len(ops))) for _ in range(POPULATION_SIZE)]
    initial_best = min(map(fitness, population))

    def tournament() -> tuple[int, ...]:
        return min(rng.sample(population, TOURNAMENT_SIZE), key=fitness)

    for _ in range(GENERATIONS):
        next_population = [min(population, key=fitness)]  # Elitismo: preserva um indivíduo.
        while len(next_population) < POPULATION_SIZE:
            parent1, parent2 = tournament(), tournament()
            if rng.random() < CROSSOVER_PROBABILITY:
                child1, child2 = ox(parent1, parent2, rng), ox(parent2, parent1, rng)
            else:
                child1, child2 = parent1, parent2
            next_population.append(swap_mutation(child1, rng))
            if len(next_population) < POPULATION_SIZE:
                next_population.append(swap_mutation(child2, rng))
        population = next_population
    best = min(population, key=fitness)
    return {
        "seed": seed,
        "initial_best": initial_best,
        "best": fitness(best),
        "genome": best,
        "unique_evaluations": len(cache),
        "elapsed_seconds": round(perf_counter() - started, 6),
    }


def rendered(schedule: list[Scheduled]) -> list[dict[str, str | int]]:
    return [
        {
            "unit": s.op.unit,
            "step": s.op.step + 1,
            "machine": s.op.machine,
            "start": s.start,
            "end": s.end,
        }
        for s in sorted(schedule, key=lambda s: (s.start, s.op.machine, s.op.unit))
    ]


def main() -> None:
    started = perf_counter()
    cases: list[dict[str, object]] = []
    results: dict[str, object] = {
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "model": (
            "Job shop, fixed machines, nonpreemptive operations, all units released at 0, "
            "no transport/setup/buffer restrictions"
        ),
        "config": {
            "population": POPULATION_SIZE,
            "generations": GENERATIONS,
            "tournament": TOURNAMENT_SIZE,
            "crossover": "OX",
            "crossover_probability": CROSSOVER_PROBABILITY,
            "mutation": "swap",
            "mutation_probability": MUTATION_PROBABILITY,
            "elite": 1,
            "seeds": SEEDS,
            "initial_population": "entirely_random",
            "seeded_with_baseline": False,
        },
        "cases": cases,
    }
    for demand in [{"E": 1, "P": 1, "S": 1}, {"E": 3, "P": 2, "S": 4}]:
        case_started = perf_counter()
        ops, units = operations(demand)
        baseline = tuple(range(len(ops)))
        baseline_schedule = decode(baseline, ops, units)
        # Neste catálogo fixo, toda unidade termina em uma única operação no Centro.
        # Carga do Centro + chegada mais cedo possível fornece um limite inferior.
        center_load = sum(op.duration for op in ops if op.machine == "Centro")
        earliest_center = min(
            sum(op.duration for op in route if op.machine != "Centro") for route in units.values()
        )
        lower_bound = center_load + earliest_center
        seeds = [run_ga(ops, units, seed) for seed in SEEDS]
        bests = [run["best"] for run in seeds]
        best_run = min(seeds, key=lambda run: run["best"])
        item: dict[str, object] = {
            "demand": demand,
            "units": len(units),
            "operations": len(ops),
            "baseline_E_P_S": makespan(baseline_schedule),
            "spt_enabled_operations": makespan(decode(baseline, ops, units, spt=True)),
            "lower_bound": lower_bound,
            "ga_min": min(bests),
            "ga_mean": mean(bests),
            "ga_worst": max(bests),
            "ga_runs": seeds,
            "baseline_schedule": rendered(baseline_schedule),
            "best_ga_schedule": rendered(decode(best_run["genome"], ops, units)),
        }
        reverse_priority = tuple(
            op.id for prefix in ["S", "P", "E"] for op in ops if op.unit.startswith(prefix)
        )
        reverse_schedule = decode(reverse_priority, ops, units)
        item["baseline_S_P_E"] = makespan(reverse_schedule)
        item["schedule_S_P_E"] = rendered(reverse_schedule)
        if len(ops) <= 7:
            distribution = Counter(
                makespan(decode(genome, ops, units)) for genome in permutations(range(len(ops)))
            )
            item["exhaustive"] = {
                "permutations": sum(distribution.values()),
                "min": min(distribution),
                "max": max(distribution),
                "makespan_distribution": dict(sorted(distribution.items())),
            }
        item["elapsed_seconds"] = round(perf_counter() - case_started, 6)
        cases.append(item)
    results["elapsed_seconds"] = round(perf_counter() - started, 6)
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
