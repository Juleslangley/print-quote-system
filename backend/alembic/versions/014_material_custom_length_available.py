"""Add custom_length_available to materials for roll.

Revision ID: 014_mat_custom_length
Revises: 013_mat_sizes_length
Create Date: 2026-02-15

When checked, roll length can be overridden in PO lines (custom lm instead of fixed roll lengths).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "014_mat_custom_length"
down_revision: Union[str, None] = "013_mat_sizes_length"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("materials", sa.Column("custom_length_available", sa.Boolean(), nullable=True, server_default="false"))


def downgrade() -> None:
    op.drop_column("materials", "custom_length_available")
