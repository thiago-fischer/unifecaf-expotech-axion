from sqlalchemy.orm import Session

from app.models.product import Product
from app.repositories.machine_repository import MachineRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.product_schema import ProductCreate


class ProductNotFoundError(Exception):
    pass


class InvalidSequenceError(Exception):
    pass


class MissingMachinesError(Exception):
    def __init__(self, machine_ids: list[int]) -> None:
        self.machine_ids = machine_ids
        super().__init__(machine_ids)


class ProductService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = ProductRepository(session)
        self.machine_repository = MachineRepository(session)

    def create(self, data: ProductCreate | dict[str, object]) -> Product:
        # Revalidate even constructed schemas for callers outside HTTP.
        data = ProductCreate.model_validate(
            data.model_dump() if isinstance(data, ProductCreate) else data
        )
        try:
            if sorted(step.sequence for step in data.steps) != list(range(1, len(data.steps) + 1)):
                raise InvalidSequenceError
            machine_ids = {step.machine_id for step in data.steps}
            missing = sorted(machine_ids - self.machine_repository.existing_ids(machine_ids))
            if missing:
                raise MissingMachinesError(missing)
            product = self.repository.add(data)
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        return product

    def list_all(self) -> list[Product]:
        return self.repository.list_all()

    def get(self, product_id: int) -> Product:
        product = self.repository.get(product_id)
        if product is None:
            raise ProductNotFoundError(product_id)
        return product
