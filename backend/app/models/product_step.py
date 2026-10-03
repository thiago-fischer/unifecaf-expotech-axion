from sqlalchemy import CheckConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class ProductStep(Base):
    __tablename__ = "product_steps"
    __table_args__ = (
        CheckConstraint("sequence > 0", name="ck_product_steps_sequence_positive"),
        CheckConstraint(
            "processing_time_seconds > 0", name="ck_product_steps_processing_time_positive"
        ),
    )

    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), primary_key=True)
    sequence: Mapped[int] = mapped_column(primary_key=True)
    machine_id: Mapped[int] = mapped_column(ForeignKey("machines.id"), nullable=False)
    processing_time_seconds: Mapped[int] = mapped_column(nullable=False)
