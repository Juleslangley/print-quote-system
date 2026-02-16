"""Test POST /api/purchase-orders/from-material: creates draft PO + one line, returns id/po_number."""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.material import Material
from app.models.purchase_order import PurchaseOrder
from app.models.purchase_order_line import PurchaseOrderLine


def test_create_po_from_material(app_with_auth_bypass, use_test_db, supplier_id, db_session):
    """
    POST /api/purchase-orders/from-material with a real material.
    Assert 200/201, po_number starts with 'PO', and exactly one line exists.
    """
    from app.models.base import new_id

    mat = Material(
        id=new_id(),
        name=f"Test Material {new_id()}",
        type="sheet",
        supplier_id=supplier_id,
        supplier="",
        active=True,
    )
    db_session.add(mat)
    db_session.commit()

    client = TestClient(app_with_auth_bypass)
    resp = client.post(
        "/api/purchase-orders/from-material",
        json={"material_id": mat.id, "qty": 1},
    )

    assert resp.status_code in (200, 201), resp.json()
    data = resp.json()
    assert "id" in data
    assert "po_number" in data
    assert str(data["po_number"]).startswith("PO"), data
    assert data.get("status") == "draft"

    po_id = data["id"]
    lines = (
        db_session.query(PurchaseOrderLine)
        .filter(PurchaseOrderLine.po_id == po_id)
        .all()
    )
    assert len(lines) == 1
    assert lines[0].material_id == mat.id
    assert lines[0].qty == 1.0

    # Cleanup
    db_session.query(PurchaseOrderLine).filter(PurchaseOrderLine.po_id == po_id).delete(synchronize_session=False)
    db_session.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).delete(synchronize_session=False)
    db_session.query(Material).filter(Material.id == mat.id).delete(synchronize_session=False)
    db_session.commit()
