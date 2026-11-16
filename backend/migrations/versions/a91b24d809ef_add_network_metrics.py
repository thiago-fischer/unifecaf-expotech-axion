"""Add sanitized network capture batches and aggregate metrics.

Revision ID: a91b24d809ef
Revises: f47c9a2e8106
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a91b24d809ef"
down_revision: str | None = "f47c9a2e8106"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "network_capture_batches",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("capture_session_id", sa.String(), nullable=False),
        sa.Column("first_sequence", sa.BigInteger(), nullable=False),
        sa.Column("last_sequence", sa.BigInteger(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("first_sequence > 0", name="ck_network_batches_first_positive"),
        sa.CheckConstraint(
            "last_sequence >= first_sequence", name="ck_network_batches_sequence_order"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "network_metric_samples",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("bucket_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_service", sa.String(length=32), nullable=False),
        sa.Column("destination_service", sa.String(length=32), nullable=False),
        sa.Column("protocol", sa.String(length=24), nullable=False),
        sa.Column("status_class", sa.String(length=3), nullable=True),
        sa.Column("request_count", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("error_count", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("bytes_total", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("retransmission_count", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("latency_sum_ms", sa.Float(), server_default="0", nullable=False),
        sa.Column("latency_count", sa.BigInteger(), server_default="0", nullable=False),
        sa.CheckConstraint("request_count >= 0", name="ck_network_metrics_requests_nonnegative"),
        sa.CheckConstraint("error_count >= 0", name="ck_network_metrics_errors_nonnegative"),
        sa.CheckConstraint("bytes_total >= 0", name="ck_network_metrics_bytes_nonnegative"),
        sa.CheckConstraint(
            "retransmission_count >= 0", name="ck_network_metrics_retransmissions_nonnegative"
        ),
        sa.CheckConstraint("latency_sum_ms >= 0", name="ck_network_metrics_latency_nonnegative"),
        sa.CheckConstraint(
            "latency_count >= 0", name="ck_network_metrics_latency_count_nonnegative"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "bucket_start",
            "source_service",
            "destination_service",
            "protocol",
            "status_class",
            name="uq_network_metrics_bucket_flow",
            postgresql_nulls_not_distinct=True,
        ),
    )
    op.create_index(
        "ix_network_metric_samples_bucket_start",
        "network_metric_samples",
        ["bucket_start"],
    )


def downgrade() -> None:
    op.drop_index("ix_network_metric_samples_bucket_start", table_name="network_metric_samples")
    op.drop_table("network_metric_samples")
    op.drop_table("network_capture_batches")
