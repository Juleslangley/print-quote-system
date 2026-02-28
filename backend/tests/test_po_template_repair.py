"""Unit tests for PO template corruption repair logic."""
from app.services.document_expand import (
    _fix_corrupted_lines_table,
    _strip_stray_if_endif_near_po_lines,
    expand_jinja_blocks,
    fix_corrupted_po_lines_block,
    repair_po_lines_html,
)
from app.services.document_blocks import BLOCK_PO_LINES


def test_repair_removes_stray_if_endif_before_po_lines():
    """Orphaned {% if lines %} before po-lines table is stripped."""
    html = (
        "<h1>PO</h1>"
        "{% if lines and (lines|length) > 0 %}"
        '<table class="po-lines"><thead><tr><th>D</th></tr></thead>'
        "<tbody>{% if lines and (lines|length) > 0 %}"
        "{% for line in lines %}<tr><td>{{ line.description }}</td></tr>{% endfor %}"
        "{% else %}<tr><td colspan=\"6\" class=\"center\">No lines</td></tr>{% endif %}"
        "</tbody></table>"
        "{% endif %}"
        "<p>Footer</p>"
    )
    out = _strip_stray_if_endif_near_po_lines(html)
    before_table = out[: out.find('<table class="po-lines">')]
    after_table = out[out.find("</table>") + len("</table>") :]
    assert "{% if lines" not in before_table
    assert "{% endif %}" not in after_table
    assert "po-lines" in out


def test_repair_removes_stray_endif_after_po_lines():
    """Orphaned {% endif %} after po-lines table is stripped."""
    html = (
        '<table class="po-lines"><thead><tr><th>D</th></tr></thead>'
        "<tbody>{% if lines and (lines|length) > 0 %}"
        "{% for line in lines %}<tr><td>{{ line.description }}</td></tr>{% endfor %}"
        "{% else %}<tr><td colspan=\"6\" class=\"center\">No lines</td></tr>{% endif %}"
        "</tbody></table>"
        "<p>gap</p>"
        "{% endif %}"
    )
    out = _strip_stray_if_endif_near_po_lines(html)
    after_table = out[out.find("</table>") + len("</table>") :]
    assert "{% endif %}" not in after_table
    assert "<p>gap</p>" in out


def test_repair_replaces_mangled_po_lines_with_canonical():
    """Empty for-loop with {{ line.* }} outside -> replaced with canonical block."""
    mangled = (
        "<h1>Header</h1>"
        "<table><tbody>"
        "{% for line in lines %} {% endfor %}"
        "<tr><td>{{ line.description }}</td></tr>"
        "</tbody></table>"
    )
    out = fix_corrupted_po_lines_block(mangled)
    assert "po-lines" in out
    loop_start = out.find("{% for line in lines %}")
    loop_end = out.find("{% endfor %}")
    assert loop_start >= 0 and loop_end > loop_start
    assert "{{ line.description" in out[loop_start:loop_end]


def test_repair_po_lines_html_full_pipeline():
    """repair_po_lines_html runs full pipeline and produces valid output."""
    corrupted = (
        "<h1>PO {{ po.po_number }}</h1>"
        "{% if lines and (lines|length) > 0 %}"
        "<table><tbody>"
        "{% for line in lines %} {% endfor %}"
        "<tr><td>{{ line.description }}</td></tr>"
        "</tbody></table>"
        "{% endif %}"
    )
    out = repair_po_lines_html(corrupted)
    assert "po-lines" in out
    assert out.count("{% for line in lines %}") == 1
    assert out.count("{% endfor %}") >= 1
    assert out.count("{% if ") >= 1
    assert out.count("{% endif %}") >= 1
    loop_start = out.find("{% for line in lines %}")
    loop_end = out.find("{% endfor %}")
    assert "{{ line." in out[loop_start:loop_end]


def test_expand_jinja_blocks_data_jinja_output_empty_wrapper():
    """<div data-jinja-output="">TABLE</div> expands to TABLE content, not literal 'true'."""
    html = f'<div data-jinja-output="">{BLOCK_PO_LINES}</div>'
    out = expand_jinja_blocks(html)
    assert "data-jinja-output" not in out
    assert "po-lines" in out
    assert "true" not in out
    assert "{% for line in lines %}" in out


def test_expand_jinja_blocks_true_attr_uses_innerHTML():
    """data-jinja-output="true" -> rewritten to "", then uses innerHTML."""
    html = '<div data-jinja-output="true"><p>inner content</p></div>'
    out = expand_jinja_blocks(html)
    assert "true" not in out
    assert "<p>inner content</p>" in out


def test_repair_preserves_totals_after_po_lines():
    """Repair does not remove po-totals block following po-lines."""
    html = (
        '<table class="po-lines"><thead><tr><th>D</th></tr></thead>'
        "<tbody>{% if lines and (lines|length) > 0 %}"
        "{% for line in lines %}<tr><td>{{ line.description }}</td></tr>{% endfor %}"
        "{% else %}<tr><td colspan=\"6\" class=\"center\">No lines</td></tr>{% endif %}"
        "</tbody></table>"
        '<div class="po-totals-wrap"><table class="po-totals"><tbody>'
        "<tr><td>Total</td><td>£{{ '%.2f'|format(po.total_gbp or 0) }}</td></tr>"
        "</tbody></table></div>"
    )
    out = repair_po_lines_html(html)
    assert "po-lines" in out
    assert "po-totals" in out
    assert out.find("po-lines") < out.find("po-totals")
