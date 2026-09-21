from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.orm import Session

from app.database.database import get_session
from app.models.machine import Machine
from app.schemas.machine_schema import MachineCreate, MachineNotFoundResponse, MachineRead
from app.services.machine_service import MachineNotFoundError, MachineService

router = APIRouter(prefix="/machines", tags=["machines"])


def get_machine_service(session: Annotated[Session, Depends(get_session)]) -> MachineService:
    return MachineService(session)


Service = Annotated[MachineService, Depends(get_machine_service)]


@router.post("", response_model=MachineRead, status_code=status.HTTP_201_CREATED)
def create_machine(data: MachineCreate, service: Service) -> Machine:
    return service.create(data.name)


@router.get("", response_model=list[MachineRead])
def list_machines(service: Service) -> list[Machine]:
    return service.list_all()


@router.get(
    "/{machine_id}",
    response_model=MachineRead,
    responses={404: {"model": MachineNotFoundResponse}},
)
def get_machine(machine_id: Annotated[int, Path(gt=0)], service: Service) -> Machine:
    try:
        return service.get(machine_id)
    except MachineNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Máquina não encontrada.") from exc
