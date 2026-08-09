"""Normalize legacy 'completed' order status to 'picked_up'.

The order lifecycle is confirmed -> preparing -> ready -> picked_up
(cancelled from any pre-terminal state); see VALID_TRANSITIONS in
app/routes/storefront_orders.py. Early demo seeding wrote rows with a
'completed' status that no code path produces or filters on, leaving
those orders invisible to the admin status tabs. Fold them into the
canonical terminal status.

Revision ID: c239a17d0b42
Revises: f5e101a05869
Create Date: 2026-08-09
"""

from alembic import op

revision = "c239a17d0b42"
down_revision = "f5e101a05869"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE orders SET status = 'picked_up' WHERE status = 'completed'")


def downgrade() -> None:
    # Irreversible data normalization: nothing distinguishes migrated rows
    # afterwards, and no code ever wrote 'completed'. Nothing to restore.
    pass
