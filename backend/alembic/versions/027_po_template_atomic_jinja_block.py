"""Repair PO templates: expand placeholders, remove stray true, repair corrupted loops, ensure one po-lines table.

Revision ID: 027_po_atomic_jinja
Revises: 026_dedup_po_lines
Create Date: 2026-02-23

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "027_po_atomic_jinja"
down_revision: Union[str, None] = "026_dedup_po_lines"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    rows = conn.execute(
        text(
            "SELECT id, template_html FROM document_templates WHERE doc_type = 'purchase_order' AND template_html IS NOT NULL"
        )
    ).fetchall()
    from app.services.document_expand import expand_jinja_blocks

    for (tid, html) in rows:
        if not html:
            continue
        cleaned = expand_jinja_blocks(html)
        if cleaned != html:
            conn.execute(
                text("UPDATE document_templates SET template_html = :body WHERE id = :tid"),
                {"body": cleaned, "tid": tid},
            )


def downgrade() -> None:
    pass
