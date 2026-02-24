"""
Atomic block registry for document templates.
Blocks stored as: <div data-jinja-block="NAME"></div> (placeholder)
Server expands via BLOCK_REGISTRY. TipTap treats blocks as immutable (atom: true).
Legacy: <div data-jinja-output="...">...</div> still supported for non-PO doc types.
"""
from __future__ import annotations

import html as html_module
import re
from typing import Dict

# Canonical PO lines table
BLOCK_PO_LINES = """<table class="po-lines"><thead><tr><th>Description</th><th>Supplier code</th><th class="right">Qty</th><th>UOM</th><th class="right">Unit cost</th><th class="right">Line total</th></tr></thead><tbody>{% if lines and (lines|length) > 0 %}
{% for line in lines %}
<tr>
<td>{{ line.description or '—' }}</td>
<td>{{ line.supplier_product_code or '—' }}</td>
<td class="right">{{ '%.2f'|format(line.qty or 0) }}</td>
<td>{{ line.uom or '—' }}</td>
<td class="right">£{{ '%.2f'|format(line.unit_cost_gbp or 0) }}</td>
<td class="right">£{{ '%.2f'|format(line.line_total_gbp or 0) }}</td>
</tr>
{% endfor %}
{% else %}
<tr><td colspan="6" class="center">No lines</td></tr>
{% endif %}
</tbody></table>"""

# PO totals box/table
BLOCK_PO_TOTALS = """<div class="po-totals-wrap"><table class="po-totals" role="table" aria-label="Totals"><tbody><tr><td>Subtotal</td><td class="right">£{{ '%.2f'|format(po.subtotal_gbp or 0) }}</td></tr><tr><td>VAT</td><td class="right">£{{ '%.2f'|format(po.vat_gbp or 0) }}</td></tr><tr class="grand"><td>Total</td><td class="right">£{{ '%.2f'|format(po.total_gbp or 0) }}</td></tr></tbody></table></div>"""

# Barcode SVG
BLOCK_BARCODE = """<div class="barcode-block">{{ job.barcode_svg }}</div>"""

BLOCK_REGISTRY: Dict[str, str] = {
    "po_lines": BLOCK_PO_LINES,
    "po_totals": BLOCK_PO_TOTALS,
    "barcode": BLOCK_BARCODE,
}


def expand_block_placeholders(html: str) -> str:
    """
    Replace <div data-jinja-block="NAME"></div> with BLOCK_REGISTRY[NAME].
    Supports po_lines, po_totals, barcode. Unknown blocks are left as-is.
    Legacy: <div data-jinja-output="...">...</div> is NOT expanded here
    (handled by document_expand for backward compatibility).
    """
    if not html:
        return html

    def replace_block(m: re.Match) -> str:
        block_name = (m.group(1) or "").strip().lower()
        content = BLOCK_REGISTRY.get(block_name)
        if content:
            return content
        return m.group(0)

    pattern = r'<div[^>]*\sdata-jinja-block=["\']([^"\']+)["\'][^>]*>[\s\S]*?</div>'
    return re.sub(pattern, replace_block, html, flags=re.IGNORECASE)


def expand_legacy_data_jinja_output(html: str) -> str:
    """
    Expand legacy <div data-jinja-output="VALUE">INNER</div>.
    - attr empty/""/"true" -> use INNER (never emit literal "true")
    - attr = "JINJA_STRING" -> use attribute value (legacy blocks)
    """
    if not html or "data-jinja-output" not in html:
        return html

    def replacer(m: re.Match) -> str:
        attr_val = (m.group(1) or "").strip()
        inner = m.group(2) or ""
        if attr_val == "" or attr_val.lower() == "true":
            return inner
        return html_module.unescape(attr_val)

    pattern = r'<div[^>]*\sdata-jinja-output="([^"]*)"[^>]*>([\s\S]*?)</div>'
    return re.sub(pattern, replacer, html, flags=re.IGNORECASE)
