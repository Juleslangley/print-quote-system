"""Deduplicate po-lines tables in purchase_order templates.

Revision ID: 026_dedup_po_lines
Revises: 025_po_fix_empty_loop
Create Date: 2026-02-23

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "026_dedup_po_lines"
down_revision: Union[str, None] = "025_po_fix_empty_loop"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    rows = conn.execute(
        text("SELECT id, template_html FROM document_templates WHERE doc_type = 'purchase_order' AND template_html IS NOT NULL")
    ).fetchall()
    # Import here to avoid needing full app context
    from app.services.document_repair import dedupe_tables

    for (tid, html) in rows:
        if not html or "po-lines" not in html:
            continue
        cleaned, _ = dedupe_tables(html, "po-lines")
        if cleaned != html:
            conn.execute(
                text("UPDATE document_templates SET template_html = :body WHERE id = :tid"),
                {"body": cleaned, "tid": tid},
            )


def downgrade() -> None:
    pass
