from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.production_order import ProductionOrder, ProductionOrderItem
from app.schemas.order_schema import OrderCreate


class OrderRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, data: OrderCreate) -> ProductionOrder:
        order = ProductionOrder(
            items=[
                ProductionOrderItem(**item.model_dump())
                for item in sorted(data.items, key=lambda item: item.product_id)
            ]
        )
        self.session.add(order)
        self.session.flush()
        return order

    def list_all(self) -> list[ProductionOrder]:
        return list(
            self.session.scalars(
                select(ProductionOrder)
                .options(selectinload(ProductionOrder.items))
                .order_by(ProductionOrder.id)
            )
        )

    def get(self, order_id: int) -> ProductionOrder | None:
        if order_id > 2**63 - 1:
            return None
        return self.session.scalar(
            select(ProductionOrder)
            .options(selectinload(ProductionOrder.items))
            .where(ProductionOrder.id == order_id)
        )
