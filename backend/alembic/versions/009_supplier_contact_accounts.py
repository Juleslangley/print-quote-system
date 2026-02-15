"""Add contact_person and accounts_email to suppliers.

Revision ID: 009_supplier_contact_accounts
Revises: 008_supplier_address
Create Date: supplier contact person and accounts email

"""
from typing import Sequence, Union

from alembic import op


revision: str = "009_supplier_contact_accounts"
down_revision: Union[str, None] = "008_supplier_address"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS contact_person VARCHAR DEFAULT ''")
    op.execute("ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS accounts_email VARCHAR DEFAULT ''")


def downgrade() -> None:
    op.execute("ALTER TABLE suppliers DROP COLUMN IF EXISTS contact_person")
    op.execute("ALTER TABLE suppliers DROP COLUMN IF EXISTS accounts_email")
