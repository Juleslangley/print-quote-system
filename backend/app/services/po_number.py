"""Concurrency-safe PO number generation using native PostgreSQL SEQUENCE purchase_orders_seq."""
from sqlalchemy import text
from sqlalchemy.orm import Session


def get_next_po_number(session: Session) -> str:
    """
    Get the next PO number from the native sequence purchase_orders_seq.
    Uses nextval() in the same transaction/session as the caller (e.g. promote).
    Format: PO{number:07d} (e.g. 1 -> PO0000001, 12 -> PO0000012).
    """
    r = session.execute(text("SELECT nextval('purchase_orders_seq')"))
    number = r.scalar()
    if number is None:
        raise RuntimeError("nextval('purchase_orders_seq') returned NULL")
    return f"PO{int(number):07d}"
