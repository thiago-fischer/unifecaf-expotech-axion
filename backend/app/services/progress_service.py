from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.progress_event import ProgressEvent
from app.repositories.order_repository import OrderRepository
from app.repositories.progress_repository import ProgressRepository
from app.schemas.progress_schema import ProgressEventCreate


class ProgressOrderNotFoundError(Exception):
    pass


class ProgressProductNotInOrderError(Exception):
    pass


class ProgressEventConflictError(Exception):
    pass


class ProgressService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.order_repository = OrderRepository(session)
        self.repository = ProgressRepository(session)

    def record(self, order_id: int, data: ProgressEventCreate) -> tuple[ProgressEvent, bool]:
        data = ProgressEventCreate.model_validate(data.model_dump())
        try:
            order = self.order_repository.get(order_id)
            if order is None:
                raise ProgressOrderNotFoundError(order_id)
            if not any(item.product_id == data.product_id for item in order.items):
                raise ProgressProductNotInOrderError(data.product_id)

            existing = self.repository.get_by_identity(data.device_id, data.event_id)
            if existing is not None:
                return self._accept_duplicate(existing, order_id, data)

            values = data.model_dump()
            values["status"] = data.status.value
            event = ProgressEvent(
                order_id=order_id,
                **values,
                received_at=datetime.now(UTC),
            )
            self.repository.add(event)
            self.session.commit()
            return event, False
        except IntegrityError:
            self.session.rollback()
            existing = self.repository.get_by_identity(data.device_id, data.event_id)
            if existing is not None:
                return self._accept_duplicate(existing, order_id, data)
            raise
        except Exception:
            self.session.rollback()
            raise

    @staticmethod
    def _accept_duplicate(
        existing: ProgressEvent, order_id: int, data: ProgressEventCreate
    ) -> tuple[ProgressEvent, bool]:
        existing_occurred_at = existing.occurred_at
        if existing_occurred_at is not None and existing_occurred_at.utcoffset() is None:
            existing_occurred_at = existing_occurred_at.replace(tzinfo=UTC)
        same_payload = (
            existing.order_id == order_id
            and existing.product_id == data.product_id
            and existing.unit_id == data.unit_id
            and existing.status == data.status.value
            and existing.step_sequence == data.step_sequence
            and existing.message == data.message
            and existing_occurred_at == data.occurred_at
        )
        if not same_payload:
            raise ProgressEventConflictError(data.event_id)
        return existing, True
