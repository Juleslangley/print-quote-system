"""Use native PostgreSQL sequence for PO numbers; drop purchase_orders_sequence and po_sequences.

Revision ID: 010_po_native_seq
Revises: 009_supplier_contact_accounts
Create Date: Native sequence purchase_orders_seq for PO numbers

- Creates sequence purchase_orders_seq (idempotent).
- Syncs sequence from existing purchase_orders so next PO number is max+1.
- Drops po_sequences and purchase_orders_sequence tables.
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text


revision: str = "010_po_native_seq"
down_revision: Union[str, None] = "009_supplier_contact_accounts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # 1) Create sequence (idempotent)
    conn.execute(text("CREATE SEQUENCE IF NOT EXISTS purchase_orders_seq START 1"))

    # 2) Sync sequence from existing data so next nextval() is max(po numeric part) + 1.
    #    Only consider rows where the numeric part is non-empty to avoid ''::int.
    conn.execute(
        text("""
            SELECT setval(
                'purchase_orders_seq',
                COALESCE(
                    (
                        SELECT MAX((regexp_replace(po_number, '\\D', '', 'g'))::integer)
                        FROM purchase_orders
                        WHERE po_number IS NOT NULL
                          AND regexp_replace(po_number, '\\D', '', 'g') ~ '^[0-9]+$'
                    ),
                    0
                )
            )
        """)
    )

    # 3) Drop custom sequence tables (order: drop indexes then tables; idempotent with IF EXISTS)
    # po_sequences has a unique index ix_po_sequences_key
    conn.execute(text("DROP TABLE IF EXISTS po_sequences CASCADE"))
    conn.execute(text("DROP TABLE IF EXISTS purchase_orders_sequence CASCADE"))


def downgrade() -> None:
    conn = op.get_bind()

    # Recreate purchase_orders_sequence (from 001)
    conn.execute(
        text("""
            CREATE TABLE IF NOT EXISTS purchase_orders_sequence (
                name VARCHAR NOT NULL PRIMARY KEY,
                next_val INTEGER DEFAULT 1
            )
        """)
    )

    # Recreate po_sequences (from 006) and seed from purchase_orders
    conn.execute(
        text("""
            CREATE TABLE IF NOT EXISTS po_sequences (
                id SERIAL PRIMARY KEY,
                key VARCHAR(64) NOT NULL,
                last_number INTEGER NOT NULL,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
            )
        """)
    )
    conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_po_sequences_key ON po_sequences (key)"))

    # Seed po_sequences from max numeric part of po_number
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
    last_number = 0 if last_number is None else int(last_number)
    conn.execute(
        text("INSERT INTO po_sequences (key, last_number) VALUES ('purchase_order', :n)"),
        {"n": last_number},
    )

    # Drop native sequence
    conn.execute(text("DROP SEQUENCE IF EXISTS purchase_orders_seq"))
