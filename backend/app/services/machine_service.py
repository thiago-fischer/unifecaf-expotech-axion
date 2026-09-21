from sqlalchemy.orm import Session

from app.models.machine import Machine
from app.repositories.machine_repository import MachineRepository
from app.schemas.machine_schema import MachineCreate


class MachineNotFoundError(Exception):
    pass


class MachineService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = MachineRepository(session)

    def create(self, name: str) -> Machine:
        # Reuse domain constraints for callers outside HTTP as well.
        data = MachineCreate(name=name)
        try:
            machine = self.repository.add(data.name)
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        return machine

    def list_all(self) -> list[Machine]:
        return self.repository.list_all()

    def get(self, machine_id: int) -> Machine:
        machine = self.repository.get(machine_id)
        if machine is None:
            raise MachineNotFoundError(machine_id)
        return machine
