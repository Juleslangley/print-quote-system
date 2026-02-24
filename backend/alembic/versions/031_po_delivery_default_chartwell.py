"""Default Delivery address to Chartwell Press HQ unless PO has delivery_name/delivery_address (drop-ship).

Revision ID: 031_po_delivery_default
Revises: 030_render_cache
Create Date: 2026-02-24

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "031_po_delivery_default"
down_revision: Union[str, None] = "030_render_cache"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Delivery block: if po has delivery_name or delivery_address, use those; else Chartwell Press HQ.
DELIVERY_BLOCK = """<div class="po-address">
<div class="label">Delivery</div>
{% if po.delivery_name or po.delivery_address %}
{% if po.delivery_name %}<div>{{ po.delivery_name }}</div>{% endif %}
{% if po.delivery_address %}<div>{{ po.delivery_address }}</div>{% endif %}
{% else %}
<div>Chartwell Press</div>
<div>171 Waterside Road</div>
<div>Hamilton Industrial Park</div>
<div>Leicester</div>
<div>LE5 1TL</div>
<div>United Kingdom</div>
{% endif %}
</div>"""


OLD_DELIVERY_BLOCK = """<div class="po-address">
<div class="label">Delivery</div>
{% if po.delivery_name %}<div>{{ po.delivery_name }}</div>{% endif %}
{% if po.delivery_address %}<div>{{ po.delivery_address }}</div>{% endif %}
</div>"""


def upgrade() -> None:
    conn = op.get_bind()
    rows = conn.execute(
        text("SELECT id, template_html FROM document_templates WHERE doc_type = 'purchase_order' AND template_html IS NOT NULL")
    ).fetchall()
    for (tid, html) in rows:
        if not html or OLD_DELIVERY_BLOCK not in html:
            continue
        new_html = html.replace(OLD_DELIVERY_BLOCK, DELIVERY_BLOCK)
        if new_html != html:
            conn.execute(
                text("UPDATE document_templates SET template_html = :body WHERE id = :tid"),
                {"body": new_html, "tid": tid},
            )


def downgrade() -> None:
    conn = op.get_bind()
    rows = conn.execute(
        text("SELECT id, template_html FROM document_templates WHERE doc_type = 'purchase_order' AND template_html IS NOT NULL")
    ).fetchall()
    for (tid, html) in rows:
        if not html or DELIVERY_BLOCK not in html:
            continue
        new_html = html.replace(DELIVERY_BLOCK, OLD_DELIVERY_BLOCK)
        if new_html != html:
            conn.execute(
                text("UPDATE document_templates SET template_html = :body WHERE id = :tid"),
                {"body": new_html, "tid": tid},
            )
