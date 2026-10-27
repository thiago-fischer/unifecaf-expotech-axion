"""Create firmware progress event ledger.

Revision ID: 2f63c1a8b4d7
Revises: f47c9a2e8106

Downgrade removes all progress history; use only with a disposable or backed-up database.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "2f63c1a8b4d7"
down_revision: str | None = "f47c9a2e8106"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "progress_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("device_id", sa.String(length=64), nullable=False),
        sa.Column("event_id", sa.String(length=64), nullable=False),
        sa.Column("unit_id", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("step_sequence", sa.Integer(), nullable=True),
        sa.Column("message", sa.String(length=500), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["order_id", "product_id"],
            ["production_order_items.order_id", "production_order_items.product_id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("device_id", "event_id", name="uq_progress_events_device_event"),
    )


def downgrade() -> None:
    op.drop_table("progress_events")
