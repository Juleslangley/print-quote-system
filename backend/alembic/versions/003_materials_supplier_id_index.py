"""add materials.supplier_id column and index if not present

Revision ID: 003_mat_supplier
Revises: 002_sync
Create Date: 2025-02-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "003_mat_supplier"
down_revision: Union[str, None] = "002_sync"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(sa.text(
        "ALTER TABLE materials ADD COLUMN IF NOT EXISTS supplier_id VARCHAR REFERENCES suppliers(id)"
    ))
    op.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS ix_materials_supplier_id ON materials (supplier_id)"
    ))


def downgrade() -> None:
    op.drop_index("ix_materials_supplier_id", table_name="materials", if_exists=True)
    op.execute(sa.text("ALTER TABLE materials DROP COLUMN IF EXISTS supplier_id"))
