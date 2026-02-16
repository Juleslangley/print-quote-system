"""Regression tests: po_number is immutable on update (400 if sent, DB unchanged)."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session, attributes

from app.main import app
from app.core.db import get_db
from app.api.deps import require_admin
from app.models.purchase_order import PurchaseOrder, IMMUTABLE_PO_NUMBER_MSG


@pytest.fixture
def mock_po():
    """A persisted PO with po_number PO0000002."""
    po = MagicMock(spec=PurchaseOrder)
    po.id = 2
    po.po_number = "PO0000002"
    po.supplier_id = "supplier-1"
    po.status = "draft"
    po.currency = "GBP"
    po.delivery_name = ""
    po.delivery_address = ""
    po.notes = ""
    po.internal_notes = ""
    po.subtotal_gbp = 0.0
    po.vat_gbp = 0.0
    po.total_gbp = 0.0
    return po


def test_update_with_po_number_in_payload_returns_400_and_db_unchanged(mock_po):
    """Attempt to update PO B with po_number of PO A: assert 400 and PO B's po_number unchanged."""
    original_po_number = "PO0000002"
    assert mock_po.po_number == original_po_number

    def fake_get_db():
        db = MagicMock(spec=Session)
        db.query.return_value.filter.return_value.first.return_value = mock_po
        yield db

    app.dependency_overrides[get_db] = fake_get_db
    app.dependency_overrides[require_admin] = lambda: None
    try:
        client = TestClient(app)
        response = client.put(
            f"/api/purchase-orders/{int(mock_po.id)}",
            json={"po_number": "PO0000001"},  # PO A's number; must not overwrite B
        )
        assert response.status_code == 400
        assert "po_number cannot be updated once created" in response.json()["detail"]
        # Regression: PO B's po_number in DB must be unchanged
        assert mock_po.po_number == original_po_number
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(require_admin, None)


def test_update_without_po_number_excludes_it_from_apply():
    """model_dump must exclude po_number so setattr never sees it."""
    from app.schemas.purchase_order import PurchaseOrderUpdate

    payload = PurchaseOrderUpdate(status="sent", po_number="PO0000001")  # po_number immutable
    data = payload.model_dump(exclude_unset=True, exclude={"po_number"})
    assert "po_number" not in data
    assert data.get("status") == "sent"


def test_orm_guard_raises_when_setting_po_number_on_persistent_instance():
    """Attribute set listener raises ValueError when po_number is set on a persistent PO (immutable)."""
    from unittest.mock import patch, MagicMock
    po = PurchaseOrder(
        id=2,
        po_number="PO0000002",
        supplier_id="supplier-1",
        status="draft",
    )
    mock_state = MagicMock()
    mock_state.persistent = True  # simulate already in DB
    with patch.object(attributes, "instance_state", return_value=mock_state):
        with pytest.raises(ValueError, match=IMMUTABLE_PO_NUMBER_MSG):
            po.po_number = "PO0000001"
