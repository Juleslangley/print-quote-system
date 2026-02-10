"""add customers.default_margin_profile_id (sync schema)

Revision ID: 002_sync
Revises: 001_add_po
Create Date: 2025-02-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "002_sync"
down_revision: Union[str, None] = "001_add_po"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(sa.text(
        "ALTER TABLE customers ADD COLUMN IF NOT EXISTS default_margin_profile_id VARCHAR"
    ))


def downgrade() -> None:
    op.execute(sa.text(
        "ALTER TABLE customers DROP COLUMN IF EXISTS default_margin_profile_id"
    ))
