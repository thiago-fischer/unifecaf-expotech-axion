from dataclasses import dataclass
from random import Random
from time import monotonic
from typing import Any

from axion_optimizer.decoder import decode, makespan, priority
from axion_optimizer.domain import Problem, Reservation


@dataclass(frozen=True)
class GAResult:
    plan: tuple[Reservation, ...]
    baselines: tuple[tuple[str, int], ...]
    metadata: dict[str, Any]


def crossover(a: tuple[str, ...], b: tuple[str, ...], rng: Random) -> tuple[str, ...]:
    if len(a) < 2:
        return a
    lo, hi = sorted(rng.sample(range(len(a)), 2))
    hi += 1
    segment = set(a[lo:hi])
    fill = [gene for gene in b[hi:] + b[:hi] if gene not in segment]
    child = list(a)
    positions = list(range(hi, len(a))) + list(range(lo))
    for position, gene in zip(positions, fill, strict=True):
        child[position] = gene
    return tuple(child)


def mutate(chromosome: tuple[str, ...], rng: Random) -> tuple[str, ...]:
    if len(chromosome) < 2:
        return chromosome
    a, b = rng.sample(range(len(chromosome)), 2)
    child = list(chromosome)
    child[a], child[b] = child[b], child[a]
    return tuple(child)


def run_ga(
    problem: Problem, seed: int, time_limit: int | None, *, generation_limit: int = 80
) -> GAResult:
    start = monotonic()
    rng = Random(seed)
    canonical, spt = priority(problem), priority(problem, spt=True)
    cache: dict[tuple[str, ...], int] = {}
    evaluations = 0

    def evaluate(chromosome: tuple[str, ...]) -> int:
        nonlocal evaluations
        if chromosome not in cache:
            plan = decode(problem, chromosome)
            cache[chromosome] = makespan(plan)
            evaluations += 1
        return cache[chromosome]

    def expired() -> bool:
        return time_limit is not None and monotonic() - start >= time_limit

    # Both references are mandatory even if preparation of a reference crosses the deadline.
    baselines = (("canonical_priority", evaluate(canonical)), ("spt", evaluate(spt)))
    population = [canonical, spt]
    best = min(population, key=evaluate)
    while len(population) < 40 and not expired():
        chromosome = tuple(rng.sample(canonical, len(canonical)))
        population.append(chromosome)
        if evaluate(chromosome) < evaluate(best):
            best = chromosome
    # Keep effective population size 40 without more evaluations after deadline.
    population.extend([best] * (40 - len(population)))
    initial_best = evaluate(best)
    completed = 0
    reason = "generation_limit"
    if len(canonical) == 1:
        reason = "trivial_instance"
    else:
        for _ in range(generation_limit):
            if expired():
                reason = "time_limit"
                break
            next_population = [best]
            while len(next_population) < 40 and not expired():
                a, b = [min(rng.choices(population, k=3), key=evaluate) for _ in range(2)]
                children = (
                    (crossover(a, b, rng), crossover(b, a, rng)) if rng.random() < 0.8 else (a, b)
                )
                for child in children:
                    if len(next_population) == 40 or expired():
                        break
                    if rng.random() < 0.2:
                        child = mutate(child, rng)
                    if evaluate(child) < evaluate(best):
                        best = child
                    next_population.append(child)
            if len(next_population) < 40:
                reason = "time_limit"
                break
            population = next_population
            completed += 1
    return GAResult(
        decode(problem, best),
        baselines,
        dict(
            profile="ga_v1",
            time_limit_seconds=time_limit,
            population_size=40,
            generation_limit=generation_limit,
            tournament_size=3,
            crossover_probability=0.8,
            mutation_probability_per_child=0.2,
            elite_count=1,
            initial_best_makespan_seconds=initial_best,
            best_makespan_seconds=evaluate(best),
            completed_generations=completed,
            evaluations=evaluations,
            elapsed_seconds=monotonic() - start,
            termination_reason=reason,
        ),
    )
