"""Repair corrupted purchase_order templates: fix TipTap-mangled po-lines Jinja.

Revision ID: 036_repair_po_lines
Revises: 035_renders_cascade
Create Date: 2026-02-23

Applies repair_po_lines_html to every purchase_order document_template and
its version rows so that corrupted {% if %}/{% for %} fragments are replaced
with the canonical po-lines block.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "036_repair_po_lines"
down_revision: Union[str, None] = "035_renders_cascade"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from app.services.document_expand import repair_po_lines_html

    conn = op.get_bind()

    rows = conn.execute(
        sa.text(
            "SELECT id, template_html FROM document_templates "
            "WHERE doc_type = 'purchase_order' AND template_html IS NOT NULL"
        )
    ).fetchall()

    for row in rows:
        tpl_id, html = row[0], row[1]
        if not html:
            continue
        repaired = repair_po_lines_html(html)
        if repaired != html:
            conn.execute(
                sa.text(
                    "UPDATE document_templates SET template_html = :html, "
                    "updated_at = CURRENT_TIMESTAMP WHERE id = :id"
                ),
                {"html": repaired, "id": tpl_id},
            )

    version_rows = conn.execute(
        sa.text(
            "SELECT v.id, v.template_html FROM document_template_versions v "
            "JOIN document_templates t ON t.id = v.template_id "
            "WHERE t.doc_type = 'purchase_order' AND v.template_html IS NOT NULL"
        )
    ).fetchall()

    for row in version_rows:
        v_id, html = row[0], row[1]
        if not html:
            continue
        repaired = repair_po_lines_html(html)
        if repaired != html:
            conn.execute(
                sa.text(
                    "UPDATE document_template_versions SET template_html = :html WHERE id = :id"
                ),
                {"html": repaired, "id": v_id},
            )


def downgrade() -> None:
    pass
