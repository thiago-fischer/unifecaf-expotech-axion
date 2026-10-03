"""create_products_and_steps

Revision ID: d8e063d489f1
Revises: 77be86445d30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d8e063d489f1"
down_revision: str | Sequence[str] | None = "77be86445d30"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "product_steps",
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("machine_id", sa.Integer(), nullable=False),
        sa.Column("processing_time_seconds", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "processing_time_seconds > 0", name="ck_product_steps_processing_time_positive"
        ),
        sa.CheckConstraint("sequence > 0", name="ck_product_steps_sequence_positive"),
        sa.ForeignKeyConstraint(
            ["machine_id"],
            ["machines.id"],
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
        ),
        sa.PrimaryKeyConstraint("product_id", "sequence"),
    )


def downgrade() -> None:
    # Removes recipes permanently; machines and their IDs are preserved.
    op.drop_table("product_steps")
    op.drop_table("products")
