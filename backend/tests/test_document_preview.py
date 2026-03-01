"""Tests for document template preview API with real PO context."""
import pytest
from fastapi.testclient import TestClient

import app.models  # noqa: F401
from app.services.document_blocks import expand_block_placeholders, expand_legacy_data_jinja_output
from app.services.document_expand import (
    _enforce_po_dom_order,
    _fix_corrupted_lines_table,
    _strip_manual_line_loops,
    expand_jinja_blocks,
)
from app.services.document_repair import (
    dedupe_tables,
    deduplicate_po_lines_tables,
    ensure_single_placeholder,
    strip_stray_line_refs,
)
from app.services.document_expand import fix_corrupted_po_lines_block
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
    assert '<table class="po-lines">' in html
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


def test_deduplicate_po_lines_tables_returns_str():
    """deduplicate_po_lines_tables returns plain string, keeps first table."""
    dup = """<p>X</p><table class="po-lines"><tbody><tr><td>1</td></tr></tbody></table>
<table class="po-lines"><tbody><tr><td>2</td></tr></tbody></table>"""
    out = deduplicate_po_lines_tables(dup)
    assert isinstance(out, str)
    assert out.count("po-lines") == 1
    assert "<tr><td>1</td></tr>" in out


def test_fix_corrupted_po_lines_block_replaces_mangled_region():
    """fix_corrupted_po_lines_block replaces corrupted block with canonical table."""
    corrupted = """<table><tbody>{% for line in lines %} {% endfor %}
<tr><td>{{ line.description }}</td></tr></tbody></table>"""
    fixed = fix_corrupted_po_lines_block(corrupted)
    assert "po-lines" in fixed
    assert "{% for line in lines %}" in fixed
    assert "{% endfor %}" in fixed
    loop_start = fixed.find("{% for line in lines %}")
    loop_end = fixed.find("{% endfor %}")
    assert "{{ line." in fixed[loop_start:loop_end]


def test_deduplicate_po_lines_keeps_first_removes_rest():
    """Multiple po-lines tables -> keep first, remove duplicates."""
    dup = """<p>Before</p>
<table class="po-lines"><thead><tr><th>Description</th></tr></thead><tbody><tr><td>1</td></tr></tbody></table>
<p>Middle</p>
<table class="po-lines"><thead><tr><th>Description</th></tr></thead><tbody><tr><td colspan="6" class="center">No lines</td></tr></tbody></table>
<p>After</p>"""
    out, _ = dedupe_tables(dup, "po-lines")
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
    out, _ = dedupe_tables(html, "po-lines")
    assert out.count("po-lines") == 1
    assert out.count("No lines") == 1, "Only the one inside canonical {% else %} should remain"
    assert "<p>Footer</p>" in out


def test_expand_data_jinja_block_po_lines():
    """data-jinja-block='po_lines' placeholder expands to canonical table."""
    html = '<div class="x" data-jinja-block="po_lines"></div>'
    out = expand_block_placeholders(html)
    assert "po-lines" in out
    assert "{% for line in lines %}" in out
    assert "data-jinja-block" not in out


def test_expand_block_placeholders_po_totals_and_barcode():
    """data-jinja-block='po_totals' and 'barcode' expand from BLOCK_REGISTRY."""
    html = '<p>X</p><div data-jinja-block="po_totals"></div><p>Y</p><div data-jinja-block="barcode"></div>'
    out = expand_block_placeholders(html)
    assert "po-totals-wrap" in out
    assert "po.subtotal_gbp" in out
    assert "job.barcode_svg" in out
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


def test_expand_data_jinja_output_empty_uses_innerHTML():
    """data-jinja-output="" wrapper: expansion uses innerHTML (canonical protected block)."""
    from app.services.document_blocks import BLOCK_PO_LINES
    html = f'<h1>Header</h1><div data-jinja-output="">{BLOCK_PO_LINES}</div><p>Footer</p>'
    out = expand_legacy_data_jinja_output(html)
    assert "data-jinja-output" not in out
    assert "po-lines" in out
    assert "{% for line in lines %}" in out
    assert "{% endif %}" in out
    assert "<h1>Header</h1>" in out and "<p>Footer</p>" in out


def test_preview_data_jinja_output_wrapper_renders_lines(
    db_session, supplier_id, app_with_auth_bypass
):
    """
    Template with <div data-jinja-output="">TABLE_HTML</div> wrapper
    renders correct line data when lines exist.
    """
    from app.services.document_blocks import BLOCK_PO_LINES

    po = PurchaseOrder(supplier_id=supplier_id, status="draft", delivery_name="D", delivery_address="A")
    db_session.add(po)
    db_session.flush()
    line = PurchaseOrderLine(
        id=new_id(),
        po_id=po.id,
        description="Wrapped Widget",
        supplier_product_code="WW1",
        qty=4,
        uom="ea",
        unit_cost_gbp=7,
        line_total_gbp=28,
        active=True,
    )
    db_session.add(line)
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
    html = res.text
    assert po.po_number in html
    assert "Wrapped Widget" in html
    assert "4" in html
    assert "28" in html or "28.00" in html
    assert "po-lines" in html
    assert "true" not in html

    db_session.query(PurchaseOrderLine).filter(PurchaseOrderLine.po_id == po.id).delete()
    db_session.query(PurchaseOrder).filter(PurchaseOrder.id == po.id).delete()
    db_session.commit()


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
    assert html.count('<table class="po-lines">') == 1, "Should render exactly one po-lines table"
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


def test_preview_prefers_template_html_when_both_provided(app_with_auth_bypass):
    """purchase_order preview ignores payload template_html/content and uses hardwired premium template."""
    client = TestClient(app_with_auth_bypass)
    res = client.post(
        "/api/document-templates/preview",
        json={
            "doc_type": "purchase_order",
            "template_html": "<p>FROM_HTML {{ po.po_number }}</p>",
            "content": "<p>FROM_CONTENT {{ po.po_number }}</p>",
        },
    )
    assert res.status_code == 200
    assert "FROM_HTML" not in res.text
    assert "FROM_CONTENT" not in res.text
    assert "Purchase Order" in res.text


def test_ensure_single_po_lines_placeholder_removes_duplicates():
    """Two placeholders -> keep first, remove rest."""
    html = (
        '<p>Before</p>'
        '<div data-jinja-block="po_lines" class="po-lines-block"></div>'
        '<p>Middle</p>'
        '<div data-jinja-block="po_lines"></div>'
        '<p>After</p>'
    )
    out, _ = ensure_single_placeholder(html, "po_lines")
    assert out.count("data-jinja-block=\"po_lines\"") == 1
    assert "Before" in out and "After" in out
    assert "Middle" in out


def test_save_po_template_two_placeholders_stores_one(
    db_session, supplier_id, app_with_auth_bypass
):
    """PUT document-templates with two po_lines placeholders -> stored has one."""
    from app.models.document_template import DocumentTemplate

    # Deactivate any existing PO template
    db_session.query(DocumentTemplate).filter(
        DocumentTemplate.doc_type == "purchase_order",
        DocumentTemplate.is_active.is_(True),
    ).update({"is_active": False}, synchronize_session=False)
    db_session.commit()

    dup_html = (
        "<h1>PO {{ po.po_number }}</h1>"
        '<div data-jinja-block="po_lines" class="po-lines-block"></div>'
        "<p>Between</p>"
        '<div data-jinja-block="po_lines"></div>'
        "<p>End</p>"
    )

    client = TestClient(app_with_auth_bypass)
    create_res = client.post(
        "/api/document-templates",
        json={
            "doc_type": "purchase_order",
            "name": "PO Two Placeholders Test",
            "template_html": dup_html,
            "template_css": "",
            "content": "",
            "is_active": True,
        },
    )
    assert create_res.status_code == 200, create_res.text
    tpl = create_res.json()
    tpl_id = tpl["id"]

    # Stored template should have been normalized to one placeholder (or expanded to one table)
    get_res = client.get(f"/api/document-templates?doc_type=purchase_order")
    assert get_res.status_code == 200
    found = next((t for t in get_res.json() if t["id"] == tpl_id), None)
    assert found is not None
    stored_html = found.get("template_html", "")

    # Either one placeholder or one expanded table (backend expands on save)
    placeholder_count = stored_html.count('data-jinja-block="po_lines"')
    po_lines_count = stored_html.count("po-lines")
    assert placeholder_count <= 1 and po_lines_count >= 1, (
        f"Expected at most one placeholder or one po-lines table, got "
        f"placeholder_count={placeholder_count} po_lines_count={po_lines_count}"
    )
    assert "true" not in stored_html, "Must not contain literal 'true'"

    # Cleanup
    client.delete(f"/api/document-templates/{tpl_id}")


def test_saving_invalid_template_returns_400(app_with_auth_bypass):
    """POST with invalid Jinja syntax returns 400 with helpful error message."""
    client = TestClient(app_with_auth_bypass)
    invalid_html = (
        '<h1>PO {{ po.po_number }}</h1>'
        '<table class="po-lines"><tbody>'
        "{% if lines %}{% for line in lines %}<tr><td>{{ line.description }}</td></tr>{% endfor %}"
        "</tbody></table>"
    )
    res = client.post(
        "/api/document-templates",
        json={
            "doc_type": "purchase_order",
            "name": "Invalid PO",
            "template_html": invalid_html,
            "template_css": "",
            "content": "",
            "is_active": False,
        },
    )
    assert res.status_code == 400
    data = res.json()
    assert "detail" in data
    assert "jinja" in data["detail"].lower() or "endif" in data["detail"].lower()


def test_put_invalid_template_returns_400(app_with_auth_bypass, supplier_id):
    """PUT with invalid Jinja syntax returns 400."""
    client = TestClient(app_with_auth_bypass)
    valid = (
        '<h1>PO {{ po.po_number }}</h1>'
        '<div data-jinja-block="po_lines"></div>'
        '<div data-jinja-block="po_totals"></div>'
    )
    create = client.post(
        "/api/document-templates",
        json={
            "doc_type": "purchase_order",
            "name": "Temp",
            "template_html": valid,
            "template_css": "",
            "content": "",
            "is_active": False,
        },
    )
    assert create.status_code == 200
    tpl_id = create.json()["id"]

    invalid_html = (
        '<h1>PO</h1><table class="po-lines"><tbody>'
        "{% if x %}<tr><td>X</td></tr>"
        "</tbody></table>"
    )
    res = client.put(
        f"/api/document-templates/{tpl_id}",
        json={"template_html": invalid_html},
    )
    assert res.status_code == 400
    client.delete(f"/api/document-templates/{tpl_id}")


def test_template_with_content_null_saves_and_renders(app_with_auth_bypass):
    """Template with content=null saves and renders using template_html only."""
    client = TestClient(app_with_auth_bypass)
    valid_html = (
        "<h1>PO {{ po.po_number }}</h1>"
        '<div data-jinja-block="po_lines"></div>'
        '<div data-jinja-block="po_totals"></div>'
    )
    create = client.post(
        "/api/document-templates",
        json={
            "doc_type": "purchase_order",
            "name": "Null Content Test",
            "template_html": valid_html,
            "template_css": "",
            "content": None,
            "is_active": False,
        },
    )
    assert create.status_code == 200
    tpl = create.json()
    assert tpl["content"] == "{}"
    assert "po-lines" in (tpl.get("template_html") or "")

    preview = client.post(
        "/api/document-templates/preview",
        json={
            "doc_type": "purchase_order",
            "template_html": valid_html,
            "template_css": None,
            "content": None,
        },
    )
    assert preview.status_code == 200
    assert "po-lines" in preview.text or "PO012345" in preview.text

    client.delete(f"/api/document-templates/{tpl['id']}")


def test_saving_template_increments_version(app_with_auth_bypass):
    """Saving a template creates a new version and increments version_num."""
    client = TestClient(app_with_auth_bypass)
    valid = (
        "<h1>PO {{ po.po_number }}</h1>"
        '<div data-jinja-block="po_lines"></div>'
        '<div data-jinja-block="po_totals"></div>'
    )
    create = client.post(
        "/api/document-templates",
        json={
            "doc_type": "purchase_order",
            "name": "Version Test",
            "template_html": valid,
            "template_css": "",
            "content": None,
            "is_active": False,
        },
    )
    assert create.status_code == 200
    tpl = create.json()
    tpl_id = tpl["id"]
    assert tpl.get("current_version_id")

    versions = client.get(f"/api/document-templates/{tpl_id}/versions").json()
    assert len(versions) >= 1
    assert versions[0]["version_num"] == 1

    update = client.put(
        f"/api/document-templates/{tpl_id}",
        json={"template_html": valid + "<p>Footer</p>", "template_css": ""},
    )
    assert update.status_code == 200
    versions2 = client.get(f"/api/document-templates/{tpl_id}/versions").json()
    assert len(versions2) >= 2
    nums = [v["version_num"] for v in versions2]
    assert 2 in nums

    client.delete(f"/api/document-templates/{tpl_id}")


def test_preview_pdf_returns_200_and_application_pdf(app_with_auth_bypass):
    """Preview with format=pdf returns 200 and application/pdf."""
    client = TestClient(app_with_auth_bypass)
    valid = (
        "<h1>PO {{ po.po_number }}</h1>"
        '<div data-jinja-block="po_lines"></div>'
        '<div data-jinja-block="po_totals"></div>'
    )
    res = client.post(
        "/api/document-templates/preview",
        params={"format": "pdf"},
        json={
            "doc_type": "purchase_order",
            "template_html": valid,
            "template_css": None,
            "content": None,
        },
    )
    assert res.status_code == 200
    assert res.headers.get("content-type", "").startswith("application/pdf")
    assert len(res.content) > 100


def test_save_po_template_without_po_lines_placeholder_returns_400(
    app_with_auth_bypass
):
    """POST/PUT purchase_order template without po_lines placeholder returns 400."""
    client = TestClient(app_with_auth_bypass)
    no_lines_html = "<h1>PO {{ po.po_number }}</h1><p>No lines block</p>"
    res = client.post(
        "/api/document-templates",
        json={
            "doc_type": "purchase_order",
            "name": "PO No Lines Block",
            "template_html": no_lines_html,
            "template_css": "",
            "content": "",
            "is_active": False,
        },
    )
    assert res.status_code == 400
    data = res.json()
    assert "detail" in data
    assert "po_lines" in data["detail"].lower() or "lines block" in data["detail"].lower()


def test_preview_data_jinja_block_produces_one_table_and_line_descriptions(
    db_session, supplier_id, app_with_auth_bypass
):
    """Preview with data-jinja-block=po_lines produces exactly one po-lines table and line descriptions."""
    po = PurchaseOrder(supplier_id=supplier_id, status="draft")
    db_session.add(po)
    db_session.flush()
    line = PurchaseOrderLine(
        id=new_id(),
        po_id=po.id,
        description="Test product A",
        supplier_product_code="SKU-A",
        qty=3,
        uom="sheet",
        unit_cost_gbp=5.0,
        line_total_gbp=15.0,
        active=True,
    )
    db_session.add(line)
    db_session.commit()
    db_session.refresh(po)

    template = (
        "<h1>PO {{ po.po_number }}</h1>"
        '<div data-jinja-block="po_lines" class="po-lines-block"></div>'
        "<p>Footer</p>"
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
    assert "Test product A" in html
    assert "3" in html
    assert "true" not in html, "No literal 'true' in output"

    db_session.query(PurchaseOrderLine).filter(PurchaseOrderLine.po_id == po.id).delete()
    db_session.query(PurchaseOrder).filter(PurchaseOrder.id == po.id).delete()
    db_session.commit()


def test_strip_stray_line_refs_outside_table():
    """{{ line.xxx }} outside po-lines table -> replaced with —; inside table preserved."""
    html = (
        '<p>Stray: {{ line.description }}</p>'
        '<table class="po-lines"><tbody>'
        "{% for line in lines %}<tr><td>{{ line.description }}</td></tr>{% endfor %}"
        "</tbody></table>"
        '<p>Also stray: {{ line.qty }}</p>'
    )
    out, _ = strip_stray_line_refs(html)
    assert "—" in out
    assert "{% for line in lines %}" in out
    assert "{{ line.description }}" in out, "Inside table preserved"


def test_double_save_valid_jinja_succeeds(app_with_auth_bypass):
    """
    Regression: saving a template with valid Jinja twice must succeed both times.
    This proves the backend doesn't corrupt the template on re-save.
    """
    client = TestClient(app_with_auth_bypass)
    valid_html = (
        "<h1>PO {{ po.po_number }}</h1>"
        '<table class="po-lines"><thead><tr><th>Desc</th><th>Qty</th></tr></thead>'
        "<tbody>"
        "{% if lines and (lines|length) > 0 %}"
        "{% for line in lines %}"
        "<tr><td>{{ line.description }}</td><td>{{ line.qty }}</td></tr>"
        "{% endfor %}"
        "{% else %}"
        '<tr><td colspan="2">No lines</td></tr>'
        "{% endif %}"
        "</tbody></table>"
    )
    create = client.post(
        "/api/document-templates",
        json={
            "doc_type": "purchase_order",
            "name": "Double Save Test",
            "template_html": valid_html,
            "template_css": "",
            "content": "{}",
            "is_active": False,
        },
    )
    assert create.status_code == 200, f"First save failed: {create.text}"
    tpl_id = create.json()["id"]
    saved_html = create.json().get("template_html", "")

    update1 = client.put(
        f"/api/document-templates/{tpl_id}",
        json={"template_html": saved_html, "content": "{}"},
    )
    assert update1.status_code == 200, f"Second save failed: {update1.text}"

    saved_html_2 = update1.json().get("template_html", "")
    update2 = client.put(
        f"/api/document-templates/{tpl_id}",
        json={"template_html": saved_html_2, "content": "{}"},
    )
    assert update2.status_code == 200, f"Third save failed: {update2.text}"

    client.delete(f"/api/document-templates/{tpl_id}")


def test_broken_jinja_missing_endif_returns_400(app_with_auth_bypass):
    """
    Update with broken Jinja (missing endif) returns 400 with an error
    message that mentions the syntax problem.
    """
    client = TestClient(app_with_auth_bypass)
    valid_html = (
        "<h1>PO {{ po.po_number }}</h1>"
        '<div data-jinja-block="po_lines"></div>'
        '<div data-jinja-block="po_totals"></div>'
    )
    create = client.post(
        "/api/document-templates",
        json={
            "doc_type": "purchase_order",
            "name": "Broken Jinja Test",
            "template_html": valid_html,
            "template_css": "",
            "content": "{}",
            "is_active": False,
        },
    )
    assert create.status_code == 200
    tpl_id = create.json()["id"]

    broken_html = (
        "<h1>PO {{ po.po_number }}</h1>"
        '<table class="po-lines"><tbody>'
        "{% if lines %}"
        "{% for line in lines %}"
        "<tr><td>{{ line.description }}</td></tr>"
        "{% endfor %}"
        "</tbody></table>"
    )
    res = client.put(
        f"/api/document-templates/{tpl_id}",
        json={"template_html": broken_html},
    )
    assert res.status_code == 400, f"Expected 400, got {res.status_code}: {res.text}"
    detail = res.json().get("detail", "")
    assert "jinja" in detail.lower() or "endif" in detail.lower() or "unexpected" in detail.lower(), (
        f"Error message should mention Jinja syntax issue: {detail}"
    )

    client.delete(f"/api/document-templates/{tpl_id}")


def test_content_null_never_persisted(app_with_auth_bypass):
    """Creating/updating with content=null must persist '{}', never NULL."""
    client = TestClient(app_with_auth_bypass)
    valid_html = (
        "<h1>PO {{ po.po_number }}</h1>"
        '<div data-jinja-block="po_lines"></div>'
        '<div data-jinja-block="po_totals"></div>'
    )
    create = client.post(
        "/api/document-templates",
        json={
            "doc_type": "purchase_order",
            "name": "Null Content Safety",
            "template_html": valid_html,
            "template_css": "",
            "content": None,
            "is_active": False,
        },
    )
    assert create.status_code == 200
    tpl = create.json()
    assert tpl["content"] is not None, "content must never be null"
    tpl_id = tpl["id"]

    update = client.put(
        f"/api/document-templates/{tpl_id}",
        json={"content": None},
    )
    assert update.status_code == 200
    assert update.json()["content"] is not None, "content must not become null on update"

    client.delete(f"/api/document-templates/{tpl_id}")


def test_save_normalizes_encoded_ops_inside_jinja(app_with_auth_bypass):
    """API save normalizes &gt;/&lt; inside Jinja tokens before storing."""
    client = TestClient(app_with_auth_bypass)
    encoded_html = (
        "<h1>PO {{ po.po_number }}</h1>"
        '<table class="po-lines"><tbody>'
        "{% if (lines|length) &gt; 0 %}"
        "{% for line in lines %}"
        "<tr><td>{{ 1 &lt; 2 }}</td><td>{{ line.description }}</td></tr>"
        "{% endfor %}"
        "{% endif %}"
        "</tbody></table>"
    )
    create = client.post(
        "/api/document-templates",
        json={
            "doc_type": "purchase_order",
            "name": "Normalize Encoded Ops",
            "template_html": encoded_html,
            "template_css": "",
            "content": "{}",
            "is_active": False,
        },
    )
    assert create.status_code == 200, create.text
    tpl = create.json()
    stored = tpl.get("template_html") or ""
    assert "{% if (lines|length) > 0 %}" in stored
    assert "{{ 1 < 2 }}" in stored
    assert "&gt;" not in stored
    assert "&lt;" not in stored

    update = client.put(
        f"/api/document-templates/{tpl['id']}",
        json={"template_html": encoded_html},
    )
    assert update.status_code == 200, update.text
    updated = update.json().get("template_html") or ""
    assert "{% if (lines|length) > 0 %}" in updated
    assert "{{ 1 < 2 }}" in updated
    assert "&gt;" not in updated
    assert "&lt;" not in updated

    client.delete(f"/api/document-templates/{tpl['id']}")
