"""Concurrency-safe PO number generation using table po_sequences only (not purchase_orders_sequence)."""
from sqlalchemy import text
from sqlalchemy.orm import Session

# Single canonical key. Do not change. Table name is po_sequences.
KEY = "purchase_order"
TABLE = "po_sequences"


def _seed_last_number_from_purchase_orders(session: Session) -> int:
    """Max numeric part of po_number where po_number LIKE 'PO%' (9-char PO + 7 digits)."""
    r = session.execute(
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
    val = r.scalar()
    return 0 if val is None else int(val)


def get_next_po_number(session: Session) -> str:
    """
    Get the next PO number from table po_sequences only (key='purchase_order').
    SELECT ... FOR UPDATE, increment last_number, return PO + 7-digit string.
    Must be called within an existing transaction (same as purchase_orders update).
    """
    # 1) Try to increment existing row in po_sequences (not purchase_orders_sequence)
    r = session.execute(
        text(
            f"""
            UPDATE {TABLE}
            SET last_number = last_number + 1
            WHERE key = :key
            RETURNING last_number
            """
        ),
        {"key": KEY},
    )
    row = r.fetchone()
    if row is not None:
        last_number = int(row[0])
        return f"PO{last_number:07d}"
    # 2) No row: seed from purchase_orders and insert into po_sequences
    last_number = _seed_last_number_from_purchase_orders(session)
    session.execute(
        text(f"INSERT INTO {TABLE} (key, last_number) VALUES (:key, :n)"),
        {"key": KEY, "n": last_number},
    )
    session.flush()
    # 3) Increment and return
    r = session.execute(
        text(
            f"""
            UPDATE {TABLE}
            SET last_number = last_number + 1
            WHERE key = :key
            RETURNING last_number
            """
        ),
        {"key": KEY},
    )
    row = r.fetchone()
    last_number = int(row[0])
    return f"PO{last_number:07d}"
