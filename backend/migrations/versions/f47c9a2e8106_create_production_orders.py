"""Create production orders and items.

Revision ID: f47c9a2e8106
Revises: bb94b7e72eb7

Downgrade removes all orders and items; use only with a disposable database.
Products, recipes and machines are preserved.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f47c9a2e8106"
down_revision: str | None = "bb94b7e72eb7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "production_orders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "production_order_items",
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_production_order_items_quantity_positive"),
        sa.ForeignKeyConstraint(["order_id"], ["production_orders.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.PrimaryKeyConstraint("order_id", "product_id"),
    )


def downgrade() -> None:
    op.drop_table("production_order_items")
    op.drop_table("production_orders")
