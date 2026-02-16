"""Tests for PO number generation from purchase_orders.id (no sequence)."""
from app.models.purchase_order import po_number_from_id


def test_po_number_from_id_format():
    """Format must be PO + 7 zero-padded digits from id."""
    assert po_number_from_id(1) == "PO0000001"
    assert po_number_from_id(2) == "PO0000002"
    assert po_number_from_id(3) == "PO0000003"


def test_po_number_from_id_single_digit():
    """First value 1 formats as PO0000001."""
    assert po_number_from_id(1) == "PO0000001"


def test_po_number_from_id_larger_number():
    """Larger numbers still get 7-digit zero-padding."""
    assert po_number_from_id(12345) == "PO0012345"
    assert po_number_from_id(9999999) == "PO9999999"
