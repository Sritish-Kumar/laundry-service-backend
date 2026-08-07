"""add email verification fields to users

Revision ID: 5c23a7f12a4b
Revises: b2c689534d23
Create Date: 2026-08-08 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "5c23a7f12a4b"
down_revision: Union[str, Sequence[str], None] = "b2c689534d23"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "users",
        sa.Column(
            "is_email_verified",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
    )
    op.add_column(
        "users",
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.alter_column("users", "is_email_verified", server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "email_verified_at")
    op.drop_column("users", "is_email_verified")
