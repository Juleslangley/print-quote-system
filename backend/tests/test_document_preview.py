"""Tests for document template preview API with real PO context."""
import pytest
from fastapi.testclient import TestClient

import app.models  # noqa: F401
from app.services.document_expand import (
    _expand_data_jinja_block,
    _enforce_po_dom_order,
    _fix_corrupted_lines_table,
    _strip_manual_line_loops,
    expand_jinja_blocks,
    deduplicate_po_lines_tables,
)
from app.models.base import new_id
from app.models.supplier import Supplier
from app.models.purchase_order import PurchaseOrder
from app.models.purchase_order_line import PurchaseOrderLine


def test_preview_with_entity_id_returns_rendered_html_with_po_number_and_lines(
    db_session, supplier_id, app_with_auth_bypass
):
    """
    Preview endpoint with doc_type=purchase_order and entity_id returns HTML
    containing po_number and a lines table.
    """
    po = PurchaseOrder(
        supplier_id=supplier_id,
        status="draft",
        delivery_name="Test Delivery",
        delivery_address="456 Road",
    )
    db_session.add(po)
    db_session.flush()
    line = PurchaseOrderLine(
        id=new_id(),
        po_id=po.id,
        description="Test product",
        supplier_product_code="SKU-X",
        qty=5,
        uom="sheet",
        unit_cost_gbp=2.50,
        line_total_gbp=12.50,
        active=True,
    )
    db_session.add(line)
    db_session.commit()
    po_id = po.id

    # PO number is set after insert
    db_session.refresh(po)

    client = TestClient(app_with_auth_bypass)
    template_html = """
    <h1>PO {{ po.po_number }}</h1>
    <table><thead><tr><th>Desc</th><th>Qty</th></tr></thead>
    <tbody>{% for line in lines %}
    <tr><td>{{ line.description }}</td><td>{{ line.qty }}</td></tr>
    {% endfor %}</tbody></table>
    """
    res = client.post(
        "/api/document-templates/preview",
        json={
            "doc_type": "purchase_order",
            "entity_id": str(po_id),
            "template_html": template_html,
            "template_css": None,
            "content": None,
        },
    )
    assert res.status_code == 200
    html = res.text

    assert po.po_number in html
    assert "Test product" in html
    assert "5" in html
    assert "<table>" in html
    assert "<tr>" in html

    # Cleanup
    db_session.query(PurchaseOrderLine).filter(PurchaseOrderLine.po_id == po_id).delete()
    db_session.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).delete()
    db_session.commit()


def test_corrupted_lines_table_fix():
    """Corrupted table (empty for loop, {{ line.* }} outside) is replaced with canonical table."""
    corrupted = """<table><thead><tr><th>Desc</th></tr></thead><tbody>
{% for line in lines %} {% endfor %}
<tr><td>{{ line.description }}</td></tr>
</tbody></table>
<table class="totals"><tr><td>Subtotal</td></tr></table>"""
    fixed = _fix_corrupted_lines_table(corrupted)
    assert "po-lines" in fixed
    assert 'class="totals"' in fixed
    assert fixed.count("{% for line in lines %}") == 1
    assert fixed.count("{% endfor %}") == 1
    # Line refs should be inside the loop now
    loop_start = fixed.find("{% for line in lines %}")
    loop_end = fixed.find("{% endfor %}")
    assert loop_start >= 0 and loop_end > loop_start
    between = fixed[loop_start:loop_end]
    assert "{{ line.description" in between


def test_preview_corrupted_template_renders_without_line_undefined(
    db_session, supplier_id, app_with_auth_bypass
):
    """Preview with corrupted template (line refs outside loop) auto-fixes and renders."""
    po = PurchaseOrder(
        supplier_id=supplier_id,
        status="draft",
        delivery_name="Test",
        delivery_address="Addr",
    )
    db_session.add(po)
    db_session.flush()
    line = PurchaseOrderLine(
        id=new_id(),
        po_id=po.id,
        description="Widget",
        supplier_product_code="W1",
        qty=2,
        uom="ea",
        unit_cost_gbp=10,
        line_total_gbp=20,
        active=True,
    )
    db_session.add(line)
    db_session.commit()
    db_session.refresh(po)

    corrupted = """<h1>PO {{ po.po_number }}</h1>
<table><tbody>{% for line in lines %} {% endfor %}
<tr><td>{{ line.description }}</td></tr></tbody></table>"""
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
    assert "line undefined" not in res.text.lower()
    assert po.po_number in res.text
    assert "Widget" in res.text


def test_deduplicate_po_lines_keeps_first_removes_rest():
    """Multiple po-lines tables -> keep first, remove duplicates."""
    dup = """<p>Before</p>
<table class="po-lines"><thead><tr><th>Description</th></tr></thead><tbody><tr><td>1</td></tr></tbody></table>
<p>Middle</p>
<table class="po-lines"><thead><tr><th>Description</th></tr></thead><tbody><tr><td colspan="6" class="center">No lines</td></tr></tbody></table>
<p>After</p>"""
    out = deduplicate_po_lines_tables(dup)
    assert out.count("po-lines") == 1
    assert "No lines" not in out
    assert "<tr><td>1</td></tr>" in out
    assert "Before" in out and "After" in out


def test_deduplicate_removes_orphan_no_lines_fragment():
    """Orphan static table with 'No lines' after canonical table is removed."""
    html = """<p>Header</p>
<table class="po-lines"><thead><tr><th>D</th></tr></thead><tbody>{% if lines %} {% for line in lines %}<tr><td>{{ line.x }}</td></tr>{% endfor %}{% else %}<tr><td colspan="6" class="center">No lines</td></tr>{% endif %}</tbody></table>
<table><tr><td colspan="6" class="center">No lines</td></tr></table>
<p>Footer</p>"""
    out = deduplicate_po_lines_tables(html)
    assert out.count("po-lines") == 1
    assert out.count("No lines") == 1, "Only the one inside canonical {% else %} should remain"
    assert "<p>Footer</p>" in out


def test_expand_data_jinja_block_po_lines():
    """data-jinja-block='po_lines' placeholder expands to canonical table."""
    html = '<div class="x" data-jinja-block="po_lines"></div>'
    out = _expand_data_jinja_block(html)
    assert "po-lines" in out
    assert "{% for line in lines %}" in out
    assert "data-jinja-block" not in out


def test_strip_manual_line_loops_removes_orphan():
    """Orphan {% for line in lines %}...{% endfor %} outside po-lines table is removed."""
    html = """<p>Before</p>
{% for line in lines %}
<div>{{ line.description }}</div>
{% endfor %}
<table class="po-lines"><tbody>{% for line in lines %}<tr><td>{{ line.x }}</td></tr>{% endfor %}</tbody></table>
<p>After</p>"""
    out = _strip_manual_line_loops(html)
    assert out.count("{% for line in lines %}") == 1
    assert "<table class=\"po-lines\">" in out
    assert "<div>{{ line.description }}</div>" not in out


def test_enforce_po_dom_order_reorders_totals_after_lines():
    """When totals table appears before po-lines, reorder so po-lines comes first."""
    wrong = """<p>Header</p>
<table class="po-totals"><tbody><tr><td>Total</td></tr></tbody></table>
<table class="po-lines"><tbody><tr><td>L1</td></tr></tbody></table>
<p>Footer</p>"""
    out = _enforce_po_dom_order(wrong)
    po_pos = out.find("po-lines")
    tot_pos = out.find("po-totals")
    assert po_pos >= 0 and tot_pos >= 0
    assert po_pos < tot_pos, "po-lines must come before po-totals"


def test_expand_jinja_blocks_data_jinja_block_po_lines():
    """Full expand: data-jinja-block='po_lines' placeholder -> canonical table."""
    html = '<h1>PO {{ po.po_number }}</h1><div data-jinja-block="po_lines"></div><p>Footer</p>'
    out = expand_jinja_blocks(html)
    assert "data-jinja-block" not in out
    assert "po-lines" in out
    assert "{% for line in lines %}" in out
    assert "<h1>" in out and "Footer" in out
    # Order: header, then table, then footer
    h1_end = out.find("</h1>") + 5
    po_lines_pos = out.find("po-lines")
    footer_pos = out.find("Footer")
    assert h1_end < po_lines_pos < footer_pos


def test_expand_jinja_blocks_never_emits_literal_true():
    """
    data-jinja-output="true", "", or missing => use innerHTML (never emit literal "true").
    data-jinja-output="<jinja>" => use attribute value (legacy).
    """
    # data-jinja-output="true" -> innerHTML, never "true"
    html = '<div data-jinja-output="true"><table class="po-lines">X</table></div>'
    out = expand_jinja_blocks(html)
    assert "true" not in out, "Must never emit literal 'true'"
    assert "<table" in out and "X" in out

    # data-jinja-output="" -> innerHTML
    html2 = '<div data-jinja-output=""><p>inner</p></div>'
    out2 = expand_jinja_blocks(html2)
    assert "<p>inner</p>" in out2

    # Legacy: data-jinja-output="JINJA" -> use attribute value
    html3 = '<div data-jinja-output="{{ foo }}">ignored</div>'
    out3 = expand_jinja_blocks(html3)
    assert "{{ foo }}" in out3
    assert "ignored" not in out3


def test_preview_deduplicates_po_lines_tables(db_session, supplier_id, app_with_auth_bypass):
    """
    Template with duplicate po-lines tables renders only one; no duplicate "No lines" when lines exist.
    """
    po = PurchaseOrder(supplier_id=supplier_id, status="draft")
    db_session.add(po)
    db_session.flush()
    line = PurchaseOrderLine(
        id=new_id(),
        po_id=po.id,
        description="Widget",
        supplier_product_code="W1",
        qty=2,
        uom="ea",
        unit_cost_gbp=10,
        line_total_gbp=20,
        active=True,
    )
    db_session.add(line)
    db_session.commit()
    db_session.refresh(po)

    # Duplicate: two po-lines tables (one with data, one "No lines")
    dup_template = (
        "<h1>PO {{ po.po_number }}</h1>"
        "<table class=\"po-lines\"><thead><tr><th>Description</th><th>Supplier code</th></tr></thead>"
        "<tbody>{% if lines and (lines|length) > 0 %}"
        "{% for line in lines %}<tr><td>{{ line.description }}</td><td>{{ line.supplier_product_code }}</td></tr>{% endfor %}"
        "{% else %}<tr><td colspan=\"6\" class=\"center\">No lines</td></tr>{% endif %}"
        "</tbody></table>"
        "<table class=\"po-lines\"><thead><tr><th>Description</th></tr></thead>"
        "<tbody><tr><td colspan=\"6\" class=\"center\">No lines</td></tr></tbody></table>"
    )

    client = TestClient(app_with_auth_bypass)
    res = client.post(
        "/api/document-templates/preview",
        json={
            "doc_type": "purchase_order",
            "entity_id": str(po.id),
            "template_html": dup_template,
            "template_css": None,
            "content": None,
        },
    )
    assert res.status_code == 200, res.text
    html = res.text
    assert po.po_number in html
    assert "Widget" in html
    assert html.count("po-lines") <= 1, "Should deduplicate to at most one po-lines table"
    # "No lines" should not appear when we have lines (first table has data; second was removed)
    assert html.count("No lines") == 0, "Should not show 'No lines' when lines exist"

    db_session.query(PurchaseOrderLine).filter(PurchaseOrderLine.po_id == po.id).delete()
    db_session.query(PurchaseOrder).filter(PurchaseOrder.id == po.id).delete()
    db_session.commit()


def test_preview_without_entity_id_uses_mock_context(db_session, app_with_auth_bypass):
    """Preview without entity_id falls back to mock context."""
    client = TestClient(app_with_auth_bypass)
    res = client.post(
        "/api/document-templates/preview",
        json={
            "doc_type": "purchase_order",
            "template_html": "<p>{{ po.po_number }}</p>",
        },
    )
    assert res.status_code == 200
    assert "PO012345" in res.text  # Mock PO number
