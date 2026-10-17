from collections import defaultdict
from dataclasses import dataclass


class PlanningError(ValueError):
    """Inconsistência da entrada, do algoritmo ou do plano."""


class PlanningLimitsError(ValueError):
    def __init__(self, violations: list[dict[str, int | str]]) -> None:
        self.violations = violations
        super().__init__(violations)


@dataclass(frozen=True)
class Step:
    sequence: int
    machine_id: int
    processing_time_seconds: int


@dataclass(frozen=True)
class Item:
    product_id: int
    product_name: str
    quantity: int
    steps: tuple[Step, ...]


@dataclass(frozen=True)
class Machine:
    machine_id: int
    machine_name: str


@dataclass(frozen=True)
class Snapshot:
    items: tuple[Item, ...]
    machines: tuple[Machine, ...]


@dataclass(frozen=True)
class Operation:
    operation_id: str
    unit_id: str
    unit_index: int
    product_id: int
    step_sequence: int
    machine_id: int
    duration_seconds: int
    predecessor_operation_id: str | None


@dataclass(frozen=True)
class Reservation:
    operation_id: str
    start_seconds: int
    end_seconds: int


@dataclass(frozen=True)
class Problem:
    snapshot: Snapshot
    operations: tuple[Operation, ...]
    unit_count: int
    horizon: int
    analytical_bound: int


LIMITS = {
    "unit_count": 100,
    "operation_count": 1000,
    "machine_count": 50,
    "horizon_seconds": 1_000_000_000,
}


def positive(value: object) -> bool:
    return type(value) is int and value > 0


def prepare(snapshot: Snapshot) -> Problem:
    """Validate integrity and count with Python integers BEFORE expanding demand."""
    if not snapshot.items or not snapshot.machines:
        raise PlanningError("Snapshot vazio")
    product_ids = [item.product_id for item in snapshot.items]
    machine_ids = [m.machine_id for m in snapshot.machines]
    if product_ids != sorted(set(product_ids)) or machine_ids != sorted(set(machine_ids)):
        raise PlanningError("IDs duplicados ou fora de ordem")
    if not all(positive(i) for i in product_ids + machine_ids):
        raise PlanningError("Identidade inválida")
    if any(
        not isinstance(m.machine_name, str) or not m.machine_name.strip() for m in snapshot.machines
    ):
        raise PlanningError("Nome de máquina inválido")
    units = count = horizon = route_bound = 0
    loads: dict[int, int] = defaultdict(int)
    for item in snapshot.items:
        if (
            not positive(item.quantity)
            or not isinstance(item.product_name, str)
            or not item.product_name.strip()
            or not item.steps
        ):
            raise PlanningError("Produto ou quantidade inválidos")
        if [s.sequence for s in item.steps] != list(range(1, len(item.steps) + 1)):
            raise PlanningError("Sequência de receita inválida")
        route = 0
        for step in item.steps:
            if (
                not positive(step.sequence)
                or not positive(step.machine_id)
                or not positive(step.processing_time_seconds)
                or step.machine_id not in machine_ids
            ):
                raise PlanningError("Etapa inválida ou máquina ausente")
            route += step.processing_time_seconds
            loads[step.machine_id] += step.processing_time_seconds * item.quantity
        units += item.quantity
        count += len(item.steps) * item.quantity
        horizon += route * item.quantity
        route_bound = max(route_bound, route)
    if set(loads) != set(machine_ids):
        raise PlanningError("Snapshot contém máquinas não utilizadas")
    actuals = dict(
        unit_count=units, operation_count=count, machine_count=len(loads), horizon_seconds=horizon
    )
    violations = [
        dict(field=field, actual=actuals[field], limit=limit)
        for field, limit in sorted(LIMITS.items())
        if actuals[field] > limit
    ]
    if violations:
        raise PlanningLimitsError(violations)
    operations = []
    for item in snapshot.items:
        for index in range(1, item.quantity + 1):
            unit_id = f"p{item.product_id}-u{index}"
            for step in item.steps:
                operations.append(
                    Operation(
                        f"{unit_id}-s{step.sequence}",
                        unit_id,
                        index,
                        item.product_id,
                        step.sequence,
                        step.machine_id,
                        step.processing_time_seconds,
                        f"{unit_id}-s{step.sequence - 1}" if step.sequence > 1 else None,
                    )
                )
    return Problem(snapshot, tuple(operations), units, horizon, max(route_bound, *loads.values()))
