from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.network import NetworkCaptureBatch, NetworkMetricSample


class NetworkRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add_batch(
        self,
        batch_id: str,
        capture_session_id: str,
        first_sequence: int,
        last_sequence: int,
        received_at: datetime,
    ) -> bool:
        statement = (
            insert(NetworkCaptureBatch)
            .values(
                id=batch_id,
                capture_session_id=capture_session_id,
                first_sequence=first_sequence,
                last_sequence=last_sequence,
                received_at=received_at,
            )
            .on_conflict_do_nothing(index_elements=[NetworkCaptureBatch.id])
            .returning(NetworkCaptureBatch.id)
        )
        return self.session.scalar(statement) is not None

    def add_metrics(self, metrics: list[dict[str, object]]) -> None:
        for values in metrics:
            statement = insert(NetworkMetricSample).values(**values)
            excluded = statement.excluded
            statement = statement.on_conflict_do_update(
                constraint="uq_network_metrics_bucket_flow",
                set_={
                    "request_count": NetworkMetricSample.request_count + excluded.request_count,
                    "error_count": NetworkMetricSample.error_count + excluded.error_count,
                    "bytes_total": NetworkMetricSample.bytes_total + excluded.bytes_total,
                    "retransmission_count": (
                        NetworkMetricSample.retransmission_count + excluded.retransmission_count
                    ),
                    "latency_sum_ms": NetworkMetricSample.latency_sum_ms + excluded.latency_sum_ms,
                    "latency_count": NetworkMetricSample.latency_count + excluded.latency_count,
                },
            )
            self.session.execute(statement)

    def delete_expired(
        self, batch_before: datetime, metric_before: datetime, limit: int = 500
    ) -> None:
        batch_ids = (
            select(NetworkCaptureBatch.id)
            .where(NetworkCaptureBatch.received_at < batch_before)
            .limit(limit)
        )
        metric_ids = (
            select(NetworkMetricSample.id)
            .where(NetworkMetricSample.bucket_start < metric_before)
            .limit(limit)
        )
        self.session.execute(
            delete(NetworkCaptureBatch).where(NetworkCaptureBatch.id.in_(batch_ids))
        )
        self.session.execute(
            delete(NetworkMetricSample).where(NetworkMetricSample.id.in_(metric_ids))
        )
