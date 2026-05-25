"""Add tags and popular columns to menu_items

Revision ID: a2b3c4d5e6f7
Revises: 28bcb522653b
Create Date: 2026-05-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "a2b3c4d5e6f7"
down_revision: Union[str, None] = "28bcb522653b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("menu_items", sa.Column("tags", postgresql.ARRAY(sa.String()), nullable=True))
    op.add_column("menu_items", sa.Column("popular", sa.Boolean(), nullable=True, server_default=sa.text("false")))


def downgrade() -> None:
    op.drop_column("menu_items", "popular")
    op.drop_column("menu_items", "tags")
