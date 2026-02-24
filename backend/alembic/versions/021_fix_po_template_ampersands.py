"""Fix ampersands in PO template that cause Jinja 'unexpected char &' error.

Revision ID: 021_po_template_amp
Revises: 020_po_template_a4
Create Date: 2026-02-23

"""
from typing import Sequence, Union

import html
import re

from alembic import op
from sqlalchemy import text

revision: str = "021_po_template_amp"
down_revision: Union[str, None] = "020_po_template_a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _fix_jinja_ampersands(s: str) -> str:
    """Replace & and && inside Jinja blocks with 'and'."""
    def fix_block(inner: str) -> str:
        inner = html.unescape(inner)
        inner = inner.replace("&&", "and")
        inner = re.sub(r"\s+&\s+", " and ", inner)
        return inner

    def fix_expr(m: re.Match) -> str:
        inner = m.group(1)
        if "&" not in inner and "&" not in html.unescape(inner):
            return m.group(0)
        return "{{" + fix_block(inner) + "}}"

    def fix_tag(m: re.Match) -> str:
        inner = m.group(1)
        if "&" not in inner and "&" not in html.unescape(inner):
            return m.group(0)
        return "{%" + fix_block(inner) + "%}"

    s = re.sub(r"\{\{(.*?)\}\}", fix_expr, s, flags=re.DOTALL)
    s = re.sub(r"\{%(.*?)%\}", fix_tag, s, flags=re.DOTALL)
    return s


def _fix_plain_ampersands(s: str) -> str:
    """Replace bare & in plain text with &amp; (company names etc)."""
    # Only in non-Jinja parts
    parts = re.split(r"(\{\{.*?\}\}|\{%.*?%\})", s, flags=re.DOTALL)
    pattern = re.compile(r"&(?!(?:amp|lt|gt|quot|#\d+);)")
    for i in range(0, len(parts), 2):
        parts[i] = pattern.sub("&amp;", parts[i])
    return "".join(parts)


def upgrade() -> None:
    conn = op.get_bind()
    rows = conn.execute(
        text("""
            SELECT id, template_html
            FROM document_templates
            WHERE doc_type = 'purchase_order'
        """)
    ).fetchall()

    for row in rows:
        tid, body = row[0], row[1]
        if not body or "&" not in body:
            continue
        fixed = _fix_jinja_ampersands(body)
        fixed = _fix_plain_ampersands(fixed)
        conn.execute(
            text("UPDATE document_templates SET template_html = :body WHERE id = :tid"),
            {"body": fixed, "tid": tid},
        )


def downgrade() -> None:
    # No automatic revert - content was fixed
    pass
