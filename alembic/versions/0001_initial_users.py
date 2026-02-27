"""initial users table

Revision ID: 0001_initial_users
Revises:
Create Date: 2026-02-27 00:00:00.000000

This migration represents the pre-existing users table. It is a no-op
because the table was created outside of Alembic version tracking.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0001_initial_users"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # users table already exists; this migration is intentionally a no-op.
    pass


def downgrade() -> None:
    pass
