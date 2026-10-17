from axion_optimizer.domain import Item, Machine, PlanningError, Snapshot, Step
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.machine import Machine as MachineModel
from app.models.product import Product
from app.repositories.order_repository import OrderRepository


class PlanningRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def snapshot(self, order_id: int) -> Snapshot | None:
        order = OrderRepository(self.session).get(order_id)
        if order is None:
            return None
        ids = [item.product_id for item in order.items]
        products: dict[int, Product] = {}
        for offset in range(0, len(ids), 500):
            products.update(
                (p.id, p)
                for p in self.session.scalars(
                    select(Product)
                    .options(selectinload(Product.steps))
                    .where(Product.id.in_(ids[offset : offset + 500]))
                )
            )
        if set(products) != set(ids):
            raise PlanningError("Produto ausente na ordem persistida")
        items = tuple(
            Item(
                item.product_id,
                products[item.product_id].name,
                item.quantity,
                tuple(
                    Step(step.sequence, step.machine_id, step.processing_time_seconds)
                    for step in products[item.product_id].steps
                ),
            )
            for item in order.items
        )
        machine_ids = sorted({s.machine_id for item in items for s in item.steps})
        machines = []
        for offset in range(0, len(machine_ids), 500):
            machines.extend(
                Machine(m.id, m.name)
                for m in self.session.scalars(
                    select(MachineModel)
                    .where(MachineModel.id.in_(machine_ids[offset : offset + 500]))
                    .order_by(MachineModel.id)
                )
            )
        return Snapshot(items, tuple(machines))
