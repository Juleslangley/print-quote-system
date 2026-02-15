"""Add address, city, postcode, country to suppliers.

Revision ID: 008_supplier_address
Revises: 007_po_sequences_consolidate
Create Date: supplier address fields

"""
from typing import Sequence, Union

from alembic import op


revision: str = "008_supplier_address"
down_revision: Union[str, None] = "007_po_sequences_consolidate"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS address VARCHAR DEFAULT ''")
    op.execute("ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS city VARCHAR DEFAULT ''")
    op.execute("ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS postcode VARCHAR DEFAULT ''")
    op.execute("ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS country VARCHAR DEFAULT ''")


def downgrade() -> None:
    op.execute("ALTER TABLE suppliers DROP COLUMN IF EXISTS address")
    op.execute("ALTER TABLE suppliers DROP COLUMN IF EXISTS city")
    op.execute("ALTER TABLE suppliers DROP COLUMN IF EXISTS postcode")
    op.execute("ALTER TABLE suppliers DROP COLUMN IF EXISTS country")
