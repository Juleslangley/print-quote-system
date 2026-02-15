"""Tests for concurrency-safe PO number generation (get_next_po_number) using po_sequences table."""
from unittest.mock import MagicMock

from app.services.po_number import get_next_po_number


def test_get_next_po_number_format():
    """Returned value must be PO + 7 zero-padded digits from po_sequences UPDATE RETURNING."""
    db = MagicMock()
    db.execute.return_value.fetchone.side_effect = [(2,), (3,)]  # UPDATE ... RETURNING last_number

    num = get_next_po_number(db)
    assert num == "PO0000002"

    num2 = get_next_po_number(db)
    assert num2 == "PO0000003"


def test_get_next_po_number_creates_row_if_missing():
    """When no row exists: UPDATE returns nothing, seed then INSERT, then UPDATE RETURNING gives 1."""
    db = MagicMock()
    # First call: UPDATE affects 0 rows -> fetchone() None; seed scalar None; INSERT; then UPDATE RETURNING (1,)
    db.execute.return_value.fetchone.side_effect = [None, (1,)]
    db.execute.return_value.scalar.return_value = None  # seed from purchase_orders

    num = get_next_po_number(db)
    assert num == "PO0000001"
    # Should have run INSERT INTO po_sequences and UPDATE po_sequences
    assert db.execute.call_count >= 2


# --- Concurrency test outline (run against real DB) ---
#
# To assert uniqueness under concurrent creates, use a test like:
#
#   @pytest.mark.skipif(not os.getenv("E2E_DB"), reason="needs E2E_DB and real DB")
#   def test_concurrent_po_creates_all_unique():
#       from app.core.db import SessionLocal
#       from app.services.po_number import get_next_po_number
#       import concurrent.futures
#
#       def create_one(_):
#           db = SessionLocal()
#           try:
#               n = get_next_po_number(db)
#               db.commit()
#               return n
#           finally:
#               db.close()
#
#       with concurrent.futures.ThreadPoolExecutor(max_workers=50) as ex:
#           results = list(ex.map(create_one, range(50)))
#
#       assert len(results) == len(set(results)), "duplicate PO numbers"
#       assert all(r.startswith("PO") and len(r) == 9 and r[2:].isdigit() for r in results)
#
# Or spawn 50 POST /api/purchase-orders requests in parallel and assert all returned
# po_numbers are unique.
