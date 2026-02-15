"""Tests for concurrency-safe PO number generation (get_next_po_number) using native sequence."""
from unittest.mock import MagicMock

from app.services.po_number import get_next_po_number


def test_get_next_po_number_format():
    """Returned value must be PO + 7 zero-padded digits from nextval('purchase_orders_seq')."""
    db = MagicMock()
    db.execute.return_value.scalar.side_effect = [2, 3]

    num = get_next_po_number(db)
    assert num == "PO0000002"

    num2 = get_next_po_number(db)
    assert num2 == "PO0000003"


def test_get_next_po_number_single_digit():
    """First value 1 formats as PO0000001."""
    db = MagicMock()
    db.execute.return_value.scalar.return_value = 1

    num = get_next_po_number(db)
    assert num == "PO0000001"


def test_get_next_po_number_larger_number():
    """Larger numbers still get 7-digit zero-padding."""
    db = MagicMock()
    db.execute.return_value.scalar.return_value = 12345

    num = get_next_po_number(db)
    assert num == "PO0012345"
