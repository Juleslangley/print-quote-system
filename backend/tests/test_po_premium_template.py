from fastapi.testclient import TestClient

from app.models.base import new_id
from app.models.purchase_order import PurchaseOrder
from app.models.purchase_order_line import PurchaseOrderLine
from app.models.supplier import Supplier


def test_po_preview_uses_hardwired_premium_template_and_default_delivery_address(
    db_session, supplier_id, app_with_auth_bypass
):
    po = PurchaseOrder(
        supplier_id=supplier_id,
        status="draft",
        delivery_name=None,
        delivery_address=None,
        notes="Handle with care",
    )
    db_session.add(po)
    db_session.flush()
    line = PurchaseOrderLine(
        id=new_id(),
        po_id=po.id,
        description="Premium test line",
        supplier_product_code="PT-001",
        qty=1,
        uom="ea",
        unit_cost_gbp=10.0,
        line_total_gbp=10.0,
        active=True,
    )
    db_session.add(line)
    db_session.commit()
    db_session.refresh(po)
    supplier = db_session.query(Supplier).filter(Supplier.id == supplier_id).first()

    client = TestClient(app_with_auth_bypass)
    res = client.post(
        "/api/document-templates/preview",
        json={
            "doc_type": "purchase_order",
            "entity_id": str(po.id),
            "template_html": "<p>this should be ignored for PO</p>",
            "template_css": "",
            "content": None,
        },
    )
    assert res.status_code == 200, res.text
    html = res.text

    assert "Purchase Order" in html
    assert "Deliver to" in html
    assert "Chartwell Press Ltd" in html
    assert "171 Waterside Road" in html
    assert "Hamilton Industrial Park" in html
    assert "Leicester" in html
    assert "LE5 1TL" in html
    assert "United Kingdom" in html
    if supplier:
        assert supplier.name in html
    assert "Premium test line" in html
    assert "£10.00" in html


def test_po_preview_computes_totals_when_missing_and_ignores_db_template_html(
    db_session, supplier_id, app_with_auth_bypass
):
    po = PurchaseOrder(
        supplier_id=supplier_id,
        status="draft",
        delivery_name="Warehouse 7",
        delivery_address="Dock Road",
        subtotal_gbp=0.0,
        vat_gbp=0.0,
        total_gbp=0.0,
    )
    db_session.add(po)
    db_session.flush()
    line = PurchaseOrderLine(
        id=new_id(),
        po_id=po.id,
        description="Fallback total line",
        supplier_product_code="FT-001",
        qty=2,
        uom="ea",
        unit_cost_gbp=15.0,
        line_total_gbp=30.0,
        active=True,
    )
    db_session.add(line)
    db_session.commit()

    client = TestClient(app_with_auth_bypass)
    res = client.post(
        "/api/document-templates/preview",
        json={
            "doc_type": "purchase_order",
            "entity_id": str(po.id),
            # Should be ignored by hardwired premium renderer
            "template_html": "<p>IGNORE ME</p>",
            "template_css": "p{color:red}",
            "content": None,
        },
    )
    assert res.status_code == 200, res.text
    html = res.text

    assert "IGNORE ME" not in html
    assert "Purchase Order" in html
    assert "Fallback total line" in html
    assert "£30.00" in html  # computed subtotal
    assert "£6.00" in html   # computed VAT @ 20%
    assert "£36.00" in html  # computed total


def test_po_preview_renders_two_lines_totals_and_default_delivery(
    db_session, supplier_id, app_with_auth_bypass
):
    po = PurchaseOrder(
        supplier_id=supplier_id,
        status="draft",
        delivery_name=None,
        delivery_address=None,
        subtotal_gbp=0.0,
        vat_gbp=0.0,
        total_gbp=0.0,
    )
    db_session.add(po)
    db_session.flush()
    db_session.add_all([
        PurchaseOrderLine(
            id=new_id(),
            po_id=po.id,
            description="Line one",
            supplier_product_code="L1",
            qty=2,
            uom="ea",
            unit_cost_gbp=12.5,
            line_total_gbp=25.0,
            active=True,
        ),
        PurchaseOrderLine(
            id=new_id(),
            po_id=po.id,
            description="Line two",
            supplier_product_code="L2",
            qty=1,
            uom="ea",
            unit_cost_gbp=15.0,
            line_total_gbp=15.0,
            active=True,
        ),
    ])
    db_session.commit()

    client = TestClient(app_with_auth_bypass)
    res = client.post(
        "/api/document-templates/preview",
        json={
            "doc_type": "purchase_order",
            "entity_id": str(po.id),
            "template_html": "<p>IGNORE ME</p>",
            "template_css": "",
            "content": None,
        },
    )
    assert res.status_code == 200, res.text
    html = res.text

    assert "Line one" in html
    assert "Line two" in html
    assert "£40.00" in html  # subtotal
    assert "£8.00" in html   # vat @20%
    assert "£48.00" in html  # total
    assert "Chartwell Press Ltd" in html
    assert "171 Waterside Road" in html
    assert "Hamilton Industrial Park" in html
    assert "Leicester" in html
    assert "LE5 1TL" in html
