from sqlalchemy.orm import Session

from app.models.production_order import ProductionOrder
from app.repositories.order_repository import OrderRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.order_schema import OrderCreate


class OrderNotFoundError(Exception):
    pass


class DuplicateProductError(Exception):
    pass


class MissingProductsError(Exception):
    def __init__(self, product_ids: list[int]) -> None:
        self.product_ids = product_ids
        super().__init__(product_ids)


class OrderService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = OrderRepository(session)
        self.product_repository = ProductRepository(session)

    def create(self, data: OrderCreate | dict[str, object]) -> ProductionOrder:
        # Revalidate constructed schemas too, for callers outside HTTP.
        data = OrderCreate.model_validate(
            data.model_dump() if isinstance(data, OrderCreate) else data
        )
        try:
            product_ids = {item.product_id for item in data.items}
            if len(product_ids) != len(data.items):
                raise DuplicateProductError
            missing = sorted(product_ids - self.product_repository.existing_ids(product_ids))
            if missing:
                raise MissingProductsError(missing)
            order = self.repository.add(data)
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        return order

    def list_all(self) -> list[ProductionOrder]:
        return self.repository.list_all()

    def get(self, order_id: int) -> ProductionOrder:
        order = self.repository.get(order_id)
        if order is None:
            raise OrderNotFoundError(order_id)
        return order
