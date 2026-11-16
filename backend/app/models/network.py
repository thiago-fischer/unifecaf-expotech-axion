from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, Float, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class NetworkCaptureBatch(Base):
    __tablename__ = "network_capture_batches"

    id: Mapped[str] = mapped_column(primary_key=True)
    capture_session_id: Mapped[str] = mapped_column(nullable=False)
    first_sequence: Mapped[int] = mapped_column(BigInteger, nullable=False)
    last_sequence: Mapped[int] = mapped_column(BigInteger, nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class NetworkMetricSample(Base):
    __tablename__ = "network_metric_samples"
    __table_args__ = (
        CheckConstraint("request_count >= 0", name="ck_network_metrics_requests_nonnegative"),
        CheckConstraint("error_count >= 0", name="ck_network_metrics_errors_nonnegative"),
        CheckConstraint("bytes_total >= 0", name="ck_network_metrics_bytes_nonnegative"),
        CheckConstraint(
            "retransmission_count >= 0", name="ck_network_metrics_retransmissions_nonnegative"
        ),
        CheckConstraint("latency_sum_ms >= 0", name="ck_network_metrics_latency_nonnegative"),
        CheckConstraint("latency_count >= 0", name="ck_network_metrics_latency_count_nonnegative"),
        UniqueConstraint(
            "bucket_start",
            "source_service",
            "destination_service",
            "protocol",
            "status_class",
            name="uq_network_metrics_bucket_flow",
            postgresql_nulls_not_distinct=True,
        ),
        Index("ix_network_metric_samples_bucket_start", "bucket_start"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    bucket_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_service: Mapped[str] = mapped_column(nullable=False)
    destination_service: Mapped[str] = mapped_column(nullable=False)
    protocol: Mapped[str] = mapped_column(nullable=False)
    status_class: Mapped[str | None]
    request_count: Mapped[int] = mapped_column(
        BigInteger, default=0, server_default="0", nullable=False
    )
    error_count: Mapped[int] = mapped_column(
        BigInteger, default=0, server_default="0", nullable=False
    )
    bytes_total: Mapped[int] = mapped_column(
        BigInteger, default=0, server_default="0", nullable=False
    )
    retransmission_count: Mapped[int] = mapped_column(
        BigInteger, default=0, server_default="0", nullable=False
    )
    latency_sum_ms: Mapped[float] = mapped_column(
        Float, default=0, server_default="0", nullable=False
    )
    latency_count: Mapped[int] = mapped_column(
        BigInteger, default=0, server_default="0", nullable=False
    )
