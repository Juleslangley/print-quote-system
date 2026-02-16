"""Add custom_length_available to material_sizes.

Revision ID: 015_mat_size_custom_len
Revises: 014_mat_custom_length
Create Date: 2026-02-15

Custom length option moved from Material to MaterialSize (per roll width).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "015_mat_size_custom_len"
down_revision: Union[str, None] = "014_mat_custom_length"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(sa.text("ALTER TABLE material_sizes ADD COLUMN IF NOT EXISTS custom_length_available BOOLEAN DEFAULT false"))


def downgrade() -> None:
    op.drop_column("material_sizes", "custom_length_available")
