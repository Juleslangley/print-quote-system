"""Recreate purchase_orders_sequence table for legacy/code that still queries it.

Revision ID: 011_recreate_po_seq_table
Revises: 010_po_native_seq
Create Date: Recreate purchase_orders_sequence so existing code (e.g. job_no) does not fail

PO numbers use the native sequence purchase_orders_seq; this table is only for backward
compatibility where something still SELECTs from purchase_orders_sequence (e.g. name='default').
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text


revision: str = "011_recreate_po_seq_table"
down_revision: Union[str, None] = "010_po_native_seq"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        text("""
            CREATE TABLE IF NOT EXISTS purchase_orders_sequence (
                name VARCHAR NOT NULL PRIMARY KEY,
                next_val INTEGER DEFAULT 1
            )
        """)
    )
    conn.execute(
        text("INSERT INTO purchase_orders_sequence (name, next_val) VALUES ('default', 1) ON CONFLICT (name) DO NOTHING")
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(text("DROP TABLE IF EXISTS purchase_orders_sequence CASCADE"))
