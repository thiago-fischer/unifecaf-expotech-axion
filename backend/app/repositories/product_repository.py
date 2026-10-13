from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.product import Product
from app.models.product_step import ProductStep
from app.schemas.product_schema import ProductCreate


class ProductRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, data: ProductCreate) -> Product:
        product = Product(
            name=data.name,
            steps=[
                ProductStep(**step.model_dump())
                for step in sorted(data.steps, key=lambda step: step.sequence)
            ],
        )
        self.session.add(product)
        self.session.flush()
        return product

    def list_all(self) -> list[Product]:
        return list(
            self.session.scalars(
                select(Product).options(selectinload(Product.steps)).order_by(Product.id)
            )
        )

    def get(self, product_id: int) -> Product | None:
        if product_id > 2**63 - 1:
            return None
        return self.session.scalar(
            select(Product).options(selectinload(Product.steps)).where(Product.id == product_id)
        )

    def existing_ids(self, product_ids: set[int]) -> set[int]:
        # Respect SQLite parameter limits and exclude IDs outside its integer range.
        ids = sorted(product_id for product_id in product_ids if product_id <= 2**63 - 1)
        existing: set[int] = set()
        for start in range(0, len(ids), 500):
            existing.update(
                self.session.scalars(
                    select(Product.id).where(Product.id.in_(ids[start : start + 500]))
                )
            )
        return existing
