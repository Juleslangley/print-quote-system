"""Add cost_per_lm_gbp and nullable height_mm to material_sizes for roll widths.

Revision ID: 012_mat_sizes_roll
Revises: 011_recreate_po_seq_table
Create Date: 2026-02-15

Supports roll materials having multiple widths (e.g. 1200, 1370, 1600mm) like sheet sizes.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "012_mat_sizes_roll"
down_revision: Union[str, None] = "011_recreate_po_seq_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("material_sizes", sa.Column("cost_per_lm_gbp", sa.Float(), nullable=True))
    op.alter_column(
        "material_sizes",
        "height_mm",
        existing_type=sa.Float(),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "material_sizes",
        "height_mm",
        existing_type=sa.Float(),
        nullable=False,
    )
    op.drop_column("material_sizes", "cost_per_lm_gbp")
