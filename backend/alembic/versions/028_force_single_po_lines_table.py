"""Force single po-lines table in purchase_order templates. Dedupe and remove orphan fallback fragments.

Revision ID: 028_force_single_po_lines
Revises: 027_po_atomic_jinja
Create Date: 2026-02-23

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "028_force_single_po_lines"
down_revision: Union[str, None] = "027_po_atomic_jinja"
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
