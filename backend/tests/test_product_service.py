from unittest.mock import patch

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.product_step import ProductStep
from app.services.machine_service import MachineService
from app.services.product_service import (
    InvalidSequenceError,
    MissingMachinesError,
    ProductNotFoundError,
    ProductService,
)


def test_service_validates_without_http(session: Session) -> None:
    service = ProductService(session)
    machine = MachineService(session).create("M")
    data = {
        "name": " P ",
        "steps": [{"sequence": 1, "machine_id": machine.id, "processing_time_seconds": 10}],
    }
    for field in ("sequence", "machine_id", "processing_time_seconds"):
        invalid = {**data, "steps": [{**data["steps"][0], field: True}]}
        with pytest.raises(ValidationError):
            service.create(invalid)
    with pytest.raises(ValidationError):
        service.create({**data, "name": " "})
    with pytest.raises(ValidationError):
        service.create({**data, "steps": ()})
    with pytest.raises(InvalidSequenceError):
        service.create({**data, "steps": [{**data["steps"][0], "sequence": 2}]})
    with pytest.raises(MissingMachinesError) as exc:
        service.create({**data, "steps": [{**data["steps"][0], "machine_id": 99}]})
    assert exc.value.machine_ids == [99]
    assert service.list_all() == []
    product = service.create(data)
    session.rollback()
    assert service.get(product.id).name == "P"
    with pytest.raises(ProductNotFoundError):
        service.get(99)


@pytest.mark.parametrize("failure_point", ["partial", "commit"])
def test_service_rolls_back_all_writes(session: Session, failure_point: str) -> None:
    machine = MachineService(session).create("M")
    service = ProductService(session)
    data = {
        "name": "P",
        "steps": [
            {"sequence": 1, "machine_id": machine.id, "processing_time_seconds": 1},
            {"sequence": 2, "machine_id": machine.id, "processing_time_seconds": 2},
        ],
    }
    error = OperationalError("simulated", {}, Exception("failure"))

    def partial(data: object) -> None:
        product = Product(name="Parcial")
        session.add(product)
        session.flush()
        session.add(
            ProductStep(
                product_id=product.id, sequence=1, machine_id=machine.id, processing_time_seconds=1
            )
        )
        session.flush()
        raise error

    target = service.repository if failure_point == "partial" else session
    method = "add" if failure_point == "partial" else "commit"
    with patch.object(target, method, side_effect=partial if method == "add" else error):
        with pytest.raises(OperationalError):
            service.create(data)
    assert not session.in_transaction()
    assert session.scalar(select(func.count()).select_from(Product)) == 0
    assert session.scalar(select(func.count()).select_from(ProductStep)) == 0
    assert MachineService(session).get(machine.id).name == "M"
    assert service.create(data).id > 0
