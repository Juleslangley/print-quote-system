"""Add po_sequences table and seed from existing purchase_orders.

Revision ID: 006_po_sequences
Revises: 005_backfill_job
Create Date: 2025-02-14

Concurrency-safe PO number generator: one row per sequence (key='purchase_order').
Seed last_number from max numeric part of existing purchase_orders.po_number so
existing POs are not broken and next number is always greater.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


revision: str = "006_po_sequences"
down_revision: Union[str, None] = "005_backfill_job"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "po_sequences",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("last_number", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_po_sequences_key"), "po_sequences", ["key"], unique=True)

    # Seed one row for purchase_order. last_number = current max numeric part of po_number, or 0.
    conn = op.get_bind()
    r = conn.execute(
        text("""
            SELECT COALESCE(MAX(
                CASE
                    WHEN po_number IS NOT NULL AND LENGTH(TRIM(po_number)) >= 9
                         AND UPPER(SUBSTRING(TRIM(po_number) FROM 1 FOR 2)) = 'PO'
                         AND SUBSTRING(TRIM(po_number) FROM 3 FOR 7) ~ '^[0-9]+$'
                    THEN CAST(SUBSTRING(TRIM(po_number) FROM 3 FOR 7) AS INTEGER)
                    ELSE NULL
                END
            ), 0)
            FROM purchase_orders
        """)
    )
    last_number = r.scalar()
    if last_number is None:
        last_number = 0
    last_number = int(last_number)
    conn.execute(text("INSERT INTO po_sequences (key, last_number) VALUES ('purchase_order', :n)"), {"n": last_number})


def downgrade() -> None:
    op.drop_index(op.f("ix_po_sequences_key"), table_name="po_sequences")
    op.drop_table("po_sequences")
