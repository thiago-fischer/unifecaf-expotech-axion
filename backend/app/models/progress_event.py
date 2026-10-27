from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKeyConstraint, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class ProgressEvent(Base):
    __tablename__ = "progress_events"
    __table_args__ = (
        ForeignKeyConstraint(
            ["order_id", "product_id"],
            ["production_order_items.order_id", "production_order_items.product_id"],
        ),
        UniqueConstraint("device_id", "event_id", name="uq_progress_events_device_event"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(nullable=False)
    product_id: Mapped[int] = mapped_column(nullable=False)
    device_id: Mapped[str] = mapped_column(String(64), nullable=False)
    event_id: Mapped[str] = mapped_column(String(64), nullable=False)
    unit_id: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    step_sequence: Mapped[int | None] = mapped_column(nullable=True)
    message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
