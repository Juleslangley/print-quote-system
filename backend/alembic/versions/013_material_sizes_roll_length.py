"""Add length_m to material_sizes for roll lengths (e.g. 20m, 50m).

Revision ID: 013_mat_sizes_length
Revises: 012_mat_sizes_roll
Create Date: 2026-02-15

Each roll width can specify a length in metres for ordering whole rolls.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "013_mat_sizes_length"
down_revision: Union[str, None] = "012_mat_sizes_roll"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("material_sizes", sa.Column("length_m", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("material_sizes", "length_m")
