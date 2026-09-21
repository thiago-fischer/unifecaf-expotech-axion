from unittest.mock import patch

import pytest
from pydantic import ValidationError
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.services.machine_service import MachineNotFoundError, MachineService


def test_service_normalizes_and_commits(session: Session) -> None:
    service = MachineService(session)
    machine = service.create("  Estação  Á  ")
    assert machine.name == "Estação  Á"
    assert machine.id > 0
    session.rollback()
    assert service.get(machine.id).name == "Estação  Á"


@pytest.mark.parametrize("name", ["", " \t ", "x" * 101, None, 123, True])
def test_service_rejects_invalid_name(session: Session, name: object) -> None:
    service = MachineService(session)
    with pytest.raises(ValidationError):
        service.create(name)  # type: ignore[arg-type]
    assert service.list_all() == []


def test_not_found_is_independent_of_http(session: Session) -> None:
    with pytest.raises(MachineNotFoundError):
        MachineService(session).get(1)


def test_rollback_after_flushed_write(session: Session) -> None:
    service = MachineService(session)
    error = OperationalError("simulated commit failure", {}, Exception("failure"))
    with patch.object(session, "commit", side_effect=error):
        with pytest.raises(OperationalError):
            service.create("Falha depois do flush")
    assert not session.in_transaction()
    assert service.list_all() == []
    assert service.create("Recuperada").id > 0
