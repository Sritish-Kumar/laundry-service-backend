"""add delivery agents to orders and fix ironing enum

Revision ID: 7207547248b9
Revises: 1556981fb91a
Create Date: 2026-08-18 00:18:01.762726

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7207547248b9'
down_revision: Union[str, Sequence[str], None] = '1556981fb91a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Postgres requires ALTER TYPE ... ADD VALUE to run outside the
    # migration's transaction block, and the new value cannot be referenced
    # in the same transaction it was added in.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE orderstatus ADD VALUE IF NOT EXISTS 'IRONING'")

    op.add_column('orders', sa.Column('pickup_agent_id', sa.Uuid(), nullable=True))
    op.add_column('orders', sa.Column('delivery_agent_id', sa.Uuid(), nullable=True))
    op.create_foreign_key(
        'orders_pickup_agent_id_fkey', 'orders', 'users', ['pickup_agent_id'], ['id']
    )
    op.create_foreign_key(
        'orders_delivery_agent_id_fkey', 'orders', 'users', ['delivery_agent_id'], ['id']
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('orders_delivery_agent_id_fkey', 'orders', type_='foreignkey')
    op.drop_constraint('orders_pickup_agent_id_fkey', 'orders', type_='foreignkey')
    op.drop_column('orders', 'delivery_agent_id')
    op.drop_column('orders', 'pickup_agent_id')

    # Postgres does not support removing a value from an existing enum type
    # without rebuilding it; the 'IRONING' value is intentionally left in
    # place on downgrade.
