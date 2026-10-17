from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class ProductionOrder(Base):
    __tablename__ = "production_orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    items: Mapped[list[ProductionOrderItem]] = relationship(
        order_by="ProductionOrderItem.product_id"
    )


class ProductionOrderItem(Base):
    __tablename__ = "production_order_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_production_order_items_quantity_positive"),
    )

    order_id: Mapped[int] = mapped_column(ForeignKey("production_orders.id"), primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), primary_key=True)
    quantity: Mapped[int] = mapped_column(nullable=False)
