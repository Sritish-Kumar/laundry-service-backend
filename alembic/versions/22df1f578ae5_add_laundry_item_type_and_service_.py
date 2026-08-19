"""add laundry item type and service pricing

Revision ID: 22df1f578ae5
Revises: 7207547248b9
Create Date: 2026-08-19 00:00:00.000000

"""
import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '22df1f578ae5'
down_revision: Union[str, Sequence[str], None] = '7207547248b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### Step 1: catalog tables ###
    op.create_table(
        'laundry_item_type',
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )

    op.create_table(
        'service_pricing',
        sa.Column('service_type_id', sa.Uuid(), nullable=False),
        sa.Column('laundry_item_type_id', sa.Uuid(), nullable=False),
        sa.Column('price', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(['service_type_id'], ['service_type.id']),
        sa.ForeignKeyConstraint(['laundry_item_type_id'], ['laundry_item_type.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'service_type_id', 'laundry_item_type_id',
            name='uq_service_pricing_service_item',
        ),
        sa.CheckConstraint('price >= 0', name='ck_service_pricing_price_non_negative'),
    )

    # ### Step 2: add new laundry_items columns as nullable so existing rows can be backfilled ###
    op.add_column('laundry_items', sa.Column('laundry_item_type_id', sa.Uuid(), nullable=True))
    op.add_column('laundry_items', sa.Column('item_type_name_snapshot', sa.String(), nullable=True))

    # ### Step 3: backfill laundry_item_type from the existing free-text cloth_type values ###
    bind = op.get_bind()

    distinct_cloth_types = bind.execute(
        sa.text("SELECT DISTINCT cloth_type FROM laundry_items WHERE cloth_type IS NOT NULL")
    ).scalars().all()

    for cloth_type in distinct_cloth_types:
        existing_id = bind.execute(
            sa.text("SELECT id FROM laundry_item_type WHERE name = :name"),
            {"name": cloth_type},
        ).scalar()

        if existing_id is None:
            existing_id = uuid.uuid4()
            bind.execute(
                sa.text(
                    "INSERT INTO laundry_item_type (id, name, is_active, created_at, updated_at) "
                    "VALUES (:id, :name, true, now(), now())"
                ),
                {"id": existing_id, "name": cloth_type},
            )

        bind.execute(
            sa.text(
                "UPDATE laundry_items "
                "SET laundry_item_type_id = :item_type_id, item_type_name_snapshot = :name "
                "WHERE cloth_type = :name"
            ),
            {"item_type_id": existing_id, "name": cloth_type},
        )

    # ### Step 4: enforce not-null now that every row has been backfilled ###
    op.alter_column('laundry_items', 'laundry_item_type_id', nullable=False)
    op.alter_column('laundry_items', 'item_type_name_snapshot', nullable=False)

    op.create_foreign_key(
        'fk_laundry_items_laundry_item_type_id',
        'laundry_items', 'laundry_item_type',
        ['laundry_item_type_id'], ['id'],
    )

    # ### Step 5: drop the now-superseded free-text/price columns ###
    op.drop_column('laundry_items', 'cloth_type')
    op.drop_column('service_type', 'current_price')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('service_type', sa.Column('current_price', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0'))
    op.add_column('laundry_items', sa.Column('cloth_type', sa.String(), nullable=True))

    bind = op.get_bind()
    bind.execute(
        sa.text(
            "UPDATE laundry_items SET cloth_type = item_type_name_snapshot"
        )
    )

    op.alter_column('laundry_items', 'cloth_type', nullable=False)
    op.alter_column('service_type', 'current_price', server_default=None)

    op.drop_constraint('fk_laundry_items_laundry_item_type_id', 'laundry_items', type_='foreignkey')
    op.drop_column('laundry_items', 'item_type_name_snapshot')
    op.drop_column('laundry_items', 'laundry_item_type_id')

    op.drop_table('service_pricing')
    op.drop_table('laundry_item_type')
