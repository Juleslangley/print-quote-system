"""Consolidate po_sequences: single row key='purchase_order', last_number = max(seq, POs).

If multiple rows exist (e.g. purchase_orders, default, etc.), keep only key='purchase_order',
set last_number to the maximum of (all last_number in po_sequences, max PO numeric in
purchase_orders), delete the others. Ensures promotion never generates a PO number that
already exists.
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text


revision: str = "007_po_sequences_consolidate"
down_revision: Union[str, None] = "006_po_sequences"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

KEY = "purchase_order"


def upgrade() -> None:
    conn = op.get_bind()

    # Max numeric part from purchase_orders where po_number LIKE 'PO%' and 9 chars
    r = conn.execute(
        text("""
            SELECT COALESCE(MAX(
                CASE
                    WHEN po_number IS NOT NULL AND LENGTH(TRIM(po_number)) = 9
                         AND UPPER(SUBSTRING(TRIM(po_number) FROM 1 FOR 2)) = 'PO'
                         AND SUBSTRING(TRIM(po_number) FROM 3 FOR 7) ~ '^[0-9]+$'
                    THEN CAST(SUBSTRING(TRIM(po_number) FROM 3 FOR 7) AS INTEGER)
                    ELSE NULL
                END
            ), 0)
            FROM purchase_orders
        """)
    )
    max_po = r.scalar()
    max_po = 0 if max_po is None else int(max_po)

    # Max last_number across all existing po_sequences rows
    r2 = conn.execute(text("SELECT COALESCE(MAX(last_number), 0) FROM po_sequences"))
    max_seq = r2.scalar()
    max_seq = 0 if max_seq is None else int(max_seq)

    last_number = max(max_po, max_seq)

    # Delete all rows (we will re-insert the single canonical row)
    conn.execute(text("DELETE FROM po_sequences"))

    # Insert single row with canonical key
    conn.execute(
        text("INSERT INTO po_sequences (key, last_number) VALUES (:key, :n)"),
        {"key": KEY, "n": last_number},
    )


def downgrade() -> None:
    # No-op: 006 already created the table and one row; we only consolidated.
    pass
