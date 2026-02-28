"""Integration tests: preview renders exactly 1 po-lines table with correct rows."""
import pytest
from fastapi.testclient import TestClient

import app.models  # noqa: F401
from app.models.base import new_id
from app.models.purchase_order import PurchaseOrder
from app.models.purchase_order_line import PurchaseOrderLine
from app.services.document_blocks import BLOCK_PO_LINES


def test_preview_wrapped_block_renders_one_table_with_correct_rows(
    db_session, supplier_id, app_with_auth_bypass
):
    """Preview: data-jinja-output="" wrapper -> 1 table, correct rows, no 'true'."""
    po = PurchaseOrder(supplier_id=supplier_id, status="draft")
    db_session.add(po)
    db_session.flush()
    for desc, code, qty, cost in [("Alpha", "A1", 2, 10), ("Beta", "B2", 5, 3)]:
        db_session.add(PurchaseOrderLine(
            id=new_id(), po_id=po.id, description=desc,
            supplier_product_code=code, qty=qty, uom="ea",
            unit_cost_gbp=cost, line_total_gbp=qty * cost, active=True,
        ))
    db_session.commit()
    db_session.refresh(po)

    template = (
        "<h1>PO {{ po.po_number }}</h1>"
        f'<div data-jinja-output="">{BLOCK_PO_LINES}</div>'
        "<p>End</p>"
    )
    client = TestClient(app_with_auth_bypass)
    res = client.post(
        "/api/document-templates/preview",
        json={
            "doc_type": "purchase_order",
            "entity_id": str(po.id),
            "template_html": template,
            "template_css": None,
            "content": None,
        },
    )
    assert res.status_code == 200, res.text
    html = res.text
    assert html.count('<table class="po-lines">') == 1, "Exactly one po-lines table"
    assert "Alpha" in html
    assert "Beta" in html
    assert "No lines" not in html
    assert "true" not in html

    db_session.query(PurchaseOrderLine).filter(PurchaseOrderLine.po_id == po.id).delete()
    db_session.query(PurchaseOrder).filter(PurchaseOrder.id == po.id).delete()
    db_session.commit()


def test_preview_corrupted_template_auto_repairs_and_renders(
    db_session, supplier_id, app_with_auth_bypass
):
    """Corrupted template (empty loop, stray line refs) auto-repairs and renders rows."""
    po = PurchaseOrder(supplier_id=supplier_id, status="draft")
    db_session.add(po)
    db_session.flush()
    db_session.add(PurchaseOrderLine(
        id=new_id(), po_id=po.id, description="Gadget",
        supplier_product_code="G1", qty=10, uom="pc",
        unit_cost_gbp=2, line_total_gbp=20, active=True,
    ))
    db_session.commit()
    db_session.refresh(po)

    corrupted = (
        "<h1>PO {{ po.po_number }}</h1>"
        "{% if lines and (lines|length) > 0 %}"
        "<table><tbody>"
        "{% for line in lines %} {% endfor %}"
        "<tr><td>{{ line.description }}</td></tr>"
        "</tbody></table>"
        "{% endif %}"
    )

    client = TestClient(app_with_auth_bypass)
    res = client.post(
        "/api/document-templates/preview",
        json={
            "doc_type": "purchase_order",
            "entity_id": str(po.id),
            "template_html": corrupted,
            "template_css": None,
            "content": None,
        },
    )
    assert res.status_code == 200, res.text
    html = res.text
    assert "Gadget" in html
    assert "line undefined" not in html.lower()
    assert "Unexpected end of template" not in html

    db_session.query(PurchaseOrderLine).filter(PurchaseOrderLine.po_id == po.id).delete()
    db_session.query(PurchaseOrder).filter(PurchaseOrder.id == po.id).delete()
    db_session.commit()


def test_preview_no_lines_shows_no_lines_message(
    db_session, supplier_id, app_with_auth_bypass
):
    """When PO has no lines, preview shows 'No lines' message."""
    po = PurchaseOrder(supplier_id=supplier_id, status="draft")
    db_session.add(po)
    db_session.commit()
    db_session.refresh(po)

    template = (
        "<h1>PO {{ po.po_number }}</h1>"
        f'<div data-jinja-output="">{BLOCK_PO_LINES}</div>'
    )
    client = TestClient(app_with_auth_bypass)
    res = client.post(
        "/api/document-templates/preview",
        json={
            "doc_type": "purchase_order",
            "entity_id": str(po.id),
            "template_html": template,
            "template_css": None,
            "content": None,
        },
    )
    assert res.status_code == 200, res.text
    assert "No lines" in res.text

    db_session.query(PurchaseOrder).filter(PurchaseOrder.id == po.id).delete()
    db_session.commit()
