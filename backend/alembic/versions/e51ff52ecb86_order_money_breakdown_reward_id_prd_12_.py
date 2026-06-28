"""order money breakdown + reward_id (PRD-12 SCRUM-76)

Revision ID: e51ff52ecb86
Revises: c9cd9d76b723
Create Date: 2026-06-28 12:42:16.812998

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e51ff52ecb86'
down_revision: Union[str, None] = 'c9cd9d76b723'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # subtotal_cents is NOT NULL with no server default. Add it nullable, backfill
    # from the existing total_cents (legacy orders had total == pre-tax subtotal),
    # then enforce NOT NULL — safe on a table that already has rows.
    op.add_column('orders', sa.Column('subtotal_cents', sa.Integer(), nullable=True))
    op.execute("UPDATE orders SET subtotal_cents = total_cents WHERE subtotal_cents IS NULL")
    op.alter_column('orders', 'subtotal_cents', nullable=False)
    op.add_column('orders', sa.Column('discount_cents', sa.Integer(), server_default=sa.text('0'), nullable=False))
    op.add_column('orders', sa.Column('tax_cents', sa.Integer(), server_default=sa.text('0'), nullable=False))
    op.add_column('orders', sa.Column('reward_id', sa.UUID(as_uuid=False), nullable=True))
    op.create_foreign_key('fk_orders_reward_id', 'orders', 'rewards', ['reward_id'], ['id'])


def downgrade() -> None:
    op.drop_constraint('fk_orders_reward_id', 'orders', type_='foreignkey')
    op.drop_column('orders', 'reward_id')
    op.drop_column('orders', 'tax_cents')
    op.drop_column('orders', 'discount_cents')
    op.drop_column('orders', 'subtotal_cents')
