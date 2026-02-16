"""Add cost_per_lm_gbp and nullable height_mm to material_sizes for roll widths.

Revision ID: 012_mat_sizes_roll
Revises: 009_supplier_contact_accounts
Create Date: 2026-02-15

Supports roll materials having multiple widths (e.g. 1200, 1370, 1600mm) like sheet sizes.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "012_mat_sizes_roll"
down_revision: Union[str, None] = "009_supplier_contact_accounts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(sa.text("ALTER TABLE material_sizes ADD COLUMN IF NOT EXISTS cost_per_lm_gbp FLOAT"))
    op.execute(sa.text("""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=current_schema() AND table_name='material_sizes' AND column_name='height_mm' AND is_nullable='NO') THEN
                ALTER TABLE material_sizes ALTER COLUMN height_mm DROP NOT NULL;
            END IF;
        END $$
    """))


def downgrade() -> None:
    op.alter_column(
        "material_sizes",
        "height_mm",
        existing_type=sa.Float(),
        nullable=False,
    )
    op.drop_column("material_sizes", "cost_per_lm_gbp")
