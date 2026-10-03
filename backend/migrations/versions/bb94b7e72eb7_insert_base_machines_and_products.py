"""insert base machines and products

Revision ID: bb94b7e72eb7
Revises: d8e063d489f1

Permanent initial catalog, separate from schema migrations. Downgrade retains
the records because names are not unique and user recipes may reference them.
Reapplying upgrade reuses matching records without overwriting user data.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import context, op

revision: str = "bb94b7e72eb7"
down_revision: str | Sequence[str] | None = "d8e063d489f1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if context.is_offline_mode():
        raise RuntimeError("A migration de dados base exige conexão com o banco (sem --sql).")

    # Keep definitions local: later changes to ORM models must not change history.
    metadata = sa.MetaData()
    machines = sa.Table(
        "machines",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String),
    )
    products = sa.Table(
        "products",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String),
    )
    steps = sa.table(
        "product_steps",
        sa.column("product_id", sa.Integer),
        sa.column("sequence", sa.Integer),
        sa.column("machine_id", sa.Integer),
        sa.column("processing_time_seconds", sa.Integer),
    )
    connection = op.get_bind()
    machine_ids: dict[str, int] = {}
    for name in ("Torno CNC", "Fresadora CNC", "Centro de Usinagem CNC"):
        machine_id = connection.scalar(
            sa.select(machines.c.id).where(machines.c.name == name).order_by(machines.c.id)
        )
        if machine_id is None:
            result = connection.execute(machines.insert().values(name=name))
            machine_id = result.inserted_primary_key[0]
        machine_ids[name] = machine_id

    recipes = (
        ("Eixo escalonado", (("Torno CNC", 10), ("Centro de Usinagem CNC", 15))),
        ("Placa de fixação", (("Fresadora CNC", 15), ("Centro de Usinagem CNC", 20))),
        (
            "Suporte usinado",
            (("Torno CNC", 10), ("Fresadora CNC", 15), ("Centro de Usinagem CNC", 20)),
        ),
    )
    for name, recipe in recipes:
        expected = [
            (sequence, machine_ids[machine_name], duration)
            for sequence, (machine_name, duration) in enumerate(recipe, 1)
        ]
        candidates = connection.scalars(sa.select(products.c.id).where(products.c.name == name))
        for product_id in candidates:
            existing = connection.execute(
                sa.select(steps.c.sequence, steps.c.machine_id, steps.c.processing_time_seconds)
                .where(steps.c.product_id == product_id)
                .order_by(steps.c.sequence)
            ).all()
            if existing == expected:
                break
        else:
            result = connection.execute(products.insert().values(name=name))
            product_id = result.inserted_primary_key[0]
            connection.execute(
                steps.insert(),
                [
                    {
                        "product_id": product_id,
                        "sequence": sequence,
                        "machine_id": machine_id,
                        "processing_time_seconds": duration,
                    }
                    for sequence, machine_id, duration in expected
                ],
            )


def downgrade() -> None:
    """Retain catalog data and references; older schema downgrades still drop tables."""
