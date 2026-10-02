from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.machine import Machine


class MachineRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, name: str) -> Machine:
        machine = Machine(name=name)
        self.session.add(machine)
        self.session.flush()
        return machine

    def list_all(self) -> list[Machine]:
        return list(self.session.scalars(select(Machine).order_by(Machine.id)))

    def get(self, machine_id: int) -> Machine | None:
        # SQLite integers are signed 64-bit; larger positive IDs cannot exist.
        if machine_id > 2**63 - 1:
            return None
        return self.session.get(Machine, machine_id)

    def existing_ids(self, machine_ids: set[int]) -> set[int]:
        # Query in batches to respect SQLite parameter limits and exclude oversized IDs.
        ids = sorted(machine_id for machine_id in machine_ids if machine_id <= 2**63 - 1)
        existing: set[int] = set()
        for start in range(0, len(ids), 500):
            existing.update(
                self.session.scalars(
                    select(Machine.id).where(Machine.id.in_(ids[start : start + 500]))
                )
            )
        return existing
