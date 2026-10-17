from bisect import insort
from collections import defaultdict

from axion_optimizer.domain import Operation, PlanningError, Problem, Reservation


def priority(problem: Problem, *, spt: bool = False) -> tuple[str, ...]:
    remaining = list(problem.operations)
    scheduled: set[str] = set()
    result = []
    while remaining:
        eligible = [
            o
            for o in remaining
            if o.predecessor_operation_id is None or o.predecessor_operation_id in scheduled
        ]
        operation = min(
            eligible,
            key=lambda o: (
                o.duration_seconds if spt else 0,
                o.product_id,
                o.unit_index,
                o.step_sequence,
            ),
        )
        result.append(operation.operation_id)
        scheduled.add(operation.operation_id)
        remaining.remove(operation)
    return tuple(result)


def decode(problem: Problem, chromosome: tuple[str, ...]) -> tuple[Reservation, ...]:
    if len(chromosome) != len(problem.operations) or set(chromosome) != {
        o.operation_id for o in problem.operations
    }:
        raise PlanningError("Cromossomo não é uma permutação")
    rank = {oid: i for i, oid in enumerate(chromosome)}
    successors: dict[str, Operation] = {}
    eligible = []
    for operation in problem.operations:
        if operation.predecessor_operation_id is None:
            eligible.append(operation)
        else:
            successors[operation.predecessor_operation_id] = operation
    ends: dict[str, int] = {}
    agendas: dict[int, list[tuple[int, int]]] = defaultdict(list)
    result = []
    while eligible:
        operation = min(eligible, key=lambda o: rank[o.operation_id])
        eligible.remove(operation)
        start = ends.get(operation.predecessor_operation_id, 0)
        agenda = agendas[operation.machine_id]
        for booked_start, booked_end in agenda:
            if start + operation.duration_seconds <= booked_start:
                break
            start = max(start, booked_end)
        end = start + operation.duration_seconds
        insort(agenda, (start, end))
        ends[operation.operation_id] = end
        result.append(Reservation(operation.operation_id, start, end))
        if operation.operation_id in successors:
            eligible.append(successors[operation.operation_id])
    return tuple(result)


def makespan(plan: tuple[Reservation, ...]) -> int:
    return max(r.end_seconds for r in plan)
