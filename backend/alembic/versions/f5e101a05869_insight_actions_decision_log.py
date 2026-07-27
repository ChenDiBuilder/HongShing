"""insight actions decision log

Revision ID: f5e101a05869
Revises: 8853d6bb2f22
Create Date: 2026-07-27 01:29:04.114791

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f5e101a05869'
down_revision: Union[str, None] = '8853d6bb2f22'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "insight_actions",
        sa.Column("id", sa.UUID(as_uuid=False), primary_key=True),
        sa.Column("insight_key", sa.String(length=50), nullable=False),
        sa.Column("action_type", sa.String(length=30), nullable=False),
        sa.Column("source_code", sa.String(length=50), nullable=False, unique=True),
        sa.Column(
            "reward_template_id",
            sa.UUID(as_uuid=False),
            sa.ForeignKey("reward_templates.id"),
            nullable=True,
        ),
        sa.Column(
            "acted_by", sa.UUID(as_uuid=False), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column("targeted_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rewards_issued", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("already_had", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sms_sent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sms_skipped", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("params", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("insight_actions")
