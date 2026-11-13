import json
from collections import defaultdict
from threading import Lock
from time import monotonic

from axion_optimizer.domain import prepare
from axion_optimizer.planner import plan_problem
from axion_optimizer.validation import validate_result
from sqlalchemy.orm import Session, sessionmaker

from app.repositories.planning_repository import PlanningRepository
from app.schemas.planning_schema import (
    MachineQueue,
    MachineQueues,
    PlanOperation,
    PlanRequest,
    PlanResponse,
)
from app.services.order_service import OrderNotFoundError

# Process-wide, including multiple app instances. No waiting queue and no DB lock during search.
_planning_lock = Lock()


class PlanningBusyError(Exception):
    pass


def build_machine_queues(plan: PlanResponse) -> MachineQueues:
    operations_by_machine: dict[int, list[PlanOperation]] = defaultdict(list)
    for operation in plan.operations:
        operations_by_machine[operation.machine_id].append(operation)
    return MachineQueues(
        order_id=plan.order_id,
        machine_queues=[
            MachineQueue(
                machine_id=machine_id,
                operations=sorted(
                    operations,
                    key=lambda operation: (operation.start_seconds, operation.operation_id),
                ),
            )
            for machine_id, operations in sorted(operations_by_machine.items())
        ],
    )


class PlanningService:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory

    def plan(self, order_id: int, data: PlanRequest) -> PlanResponse:
        data = PlanRequest.model_validate(data.model_dump())
        started = monotonic()
        with self.session_factory() as session:
            snapshot = PlanningRepository(session).snapshot(order_id)
            if snapshot is None:
                raise OrderNotFoundError(order_id)
            problem = prepare(snapshot)
        if not _planning_lock.acquire(blocking=False):
            raise PlanningBusyError
        try:
            result = plan_problem(
                problem,
                order_id,
                data.seed,
                data.ga_time_limit_seconds,
                data.certification_time_limit_seconds,
                started_at=started,
            )
            response = PlanResponse.model_validate_json(json.dumps(result))
            validate_result(problem, response.model_dump())
            response.search.total_planning_seconds = monotonic() - started
            return response
        finally:
            _planning_lock.release()
