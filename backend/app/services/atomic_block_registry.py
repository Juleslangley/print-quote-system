"""
Atomic block registry for document templates.
Blocks stored as: <div data-jinja-output="block_name">RAW HTML</div>
TipTap treats these as immutable (atom: true). Backend expands by block name.
"""
from __future__ import annotations

from typing import Dict

# Canonical PO lines table - single self-contained block
LINE_ITEMS_PO = """<table class="po-lines"><thead><tr><th>Description</th><th>Supplier code</th><th class="right">Qty</th><th>UOM</th><th class="right">Unit cost</th><th class="right">Line total</th></tr></thead><tbody>{% if lines and (lines|length) > 0 %}
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

# PO totals block
TOTALS_PO = """<div class="po-totals-wrap"><table class="po-totals" role="table" aria-label="Totals"><tbody><tr><td>Subtotal</td><td class="right">£{{ '%.2f'|format(po.subtotal_gbp or 0) }}</td></tr><tr><td>VAT</td><td class="right">£{{ '%.2f'|format(po.vat_gbp or 0) }}</td></tr><tr class="grand"><td>Total</td><td class="right">£{{ '%.2f'|format(po.total_gbp or 0) }}</td></tr></tbody></table></div>"""

# Generic totals block (quote/invoice)
TOTALS_GENERIC = """<div class="totals-block">£{{ (po.total_gbp or quote.total_sell or 0)|default(0) }}</div>"""

# Barcode block
BARCODE = """<div class="barcode-block">{{ job.barcode_svg }}</div>"""

# Store packing table
STORE_PACKING = """<table class="store-packing-table"><tbody>{% for store in batch.stores %}<tr><td>{{ store.store_name }}</td></tr>{% for item in store.line_items %}<tr><td>{{ item.component }}</td><td>{{ item.description }}</td><td>{{ item.qty }}</td></tr>{% endfor %}{% endfor %}</tbody></table>"""

# Production components placeholder
PRODUCTION_COMPONENTS = """<div class="production-components">{% if batch and batch.stores %}{% for store in batch.stores %}<div class="store-section"><h4>{{ store.store_name }}</h4>{% for item in store.line_items %}<div>{{ item.component }} — {{ item.description }} × {{ item.qty }}</div>{% endfor %}</div>{% endfor %}{% endif %}</div>"""


ATOMIC_BLOCKS: Dict[str, str] = {
    "line_items": LINE_ITEMS_PO,
    "line_items_po": LINE_ITEMS_PO,
    "po_lines": LINE_ITEMS_PO,
    "totals": TOTALS_PO,
    "totals_po": TOTALS_PO,
    "totals_generic": TOTALS_GENERIC,
    "barcode": BARCODE,
    "store_packing": STORE_PACKING,
    "production_components": PRODUCTION_COMPONENTS,
}

BLOCK_NAMES = list(ATOMIC_BLOCKS.keys())


def get_block_html(block_name: str) -> str | None:
    """Return canonical HTML for block name, or None if unknown."""
    return ATOMIC_BLOCKS.get(block_name)


def expand_block(block_name: str, raw_html: str | None = None) -> str:
    """
    Expand atomic block by name. Uses registry content; raw_html override for custom blocks.
    """
    canonical = get_block_html(block_name)
    if canonical:
        return canonical
    return raw_html or ""
