from unittest.mock import patch

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.production_order import ProductionOrder, ProductionOrderItem
from app.repositories.product_repository import ProductRepository
from app.schemas.order_schema import OrderCreate, OrderItemCreate
from app.services.machine_service import MachineService
from app.services.order_service import (
    DuplicateProductError,
    MissingProductsError,
    OrderNotFoundError,
    OrderService,
)
from app.services.product_service import ProductService


@pytest.fixture
def product(session: Session) -> Product:
    machine = MachineService(session).create("M")
    return ProductService(session).create(
        {
            "name": "P",
            "steps": [{"sequence": 1, "machine_id": machine.id, "processing_time_seconds": 10}],
        }
    )


def test_service_validates_without_http(session: Session, product: Product) -> None:
    service = OrderService(session)
    item = {"product_id": product.id, "quantity": 2}
    for invalid in [
        {},
        {"items": []},
        {"items": ()},
        {"items": [{**item, "quantity": True}]},
        {"items": [{**item, "product_id": "1"}]},
        OrderCreate.model_construct(items=[]),
        OrderCreate.model_construct(
            items=[OrderItemCreate.model_construct(**{**item, "quantity": 0})]
        ),
    ]:
        with pytest.raises(ValidationError):
            service.create(invalid)
    with patch.object(service.product_repository, "existing_ids") as lookup:
        with pytest.raises(DuplicateProductError):
            service.create({"items": [item, item]})
        lookup.assert_not_called()
    with pytest.raises(MissingProductsError) as exc:
        service.create({"items": [{"product_id": pid, "quantity": 1} for pid in [12, 9, 2**80]]})
    assert exc.value.product_ids == [9, 12, 2**80]
    assert service.list_all() == []
    order = service.create(OrderCreate.model_validate({"items": [item]}))
    session.rollback()
    session.expire_all()
    assert service.get(order.id).items[0].quantity == 2
    with pytest.raises(OrderNotFoundError):
        service.get(2**80)


@pytest.mark.parametrize("failure_point", ["partial", "commit"])
def test_service_rolls_back_all_writes(
    session: Session, product: Product, failure_point: str
) -> None:
    service = OrderService(session)
    data = {"items": [{"product_id": product.id, "quantity": 2}]}
    error = OperationalError("simulated", {}, Exception("failure"))

    def partial(data: OrderCreate) -> None:
        order = ProductionOrder()
        session.add(order)
        session.flush()
        session.add(ProductionOrderItem(order_id=order.id, **data.items[0].model_dump()))
        session.flush()
        raise error

    target = service.repository if failure_point == "partial" else session
    method = "add" if failure_point == "partial" else "commit"
    with patch.object(target, method, side_effect=partial if method == "add" else error):
        with pytest.raises(OperationalError):
            service.create(data)
    assert not session.in_transaction()
    assert session.scalar(select(func.count()).select_from(ProductionOrder)) == 0
    assert session.scalar(select(func.count()).select_from(ProductionOrderItem)) == 0
    assert ProductService(session).get(product.id).name == "P"
    assert service.create(data).id > 0


def test_product_lookup_batches(session: Session) -> None:
    products = [Product(name=f"P{i}") for i in range(1001)]
    session.add_all(products)
    session.commit()
    ids = {product.id for product in products}
    repository = ProductRepository(session)
    assert repository.existing_ids(ids | {9999, 2**80}) == ids
    assert repository.existing_ids(set()) == set()
