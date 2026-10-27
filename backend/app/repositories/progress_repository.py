from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.progress_event import ProgressEvent


class ProgressRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_identity(self, device_id: str, event_id: str) -> ProgressEvent | None:
        return self.session.scalar(
            select(ProgressEvent).where(
                ProgressEvent.device_id == device_id,
                ProgressEvent.event_id == event_id,
            )
        )

    def add(self, event: ProgressEvent) -> ProgressEvent:
        self.session.add(event)
        self.session.flush()
        return event
