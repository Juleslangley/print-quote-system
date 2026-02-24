"""Make document_templates.content nullable with default '{}'.

Revision ID: 033_content_nullable
Revises: 032_po_gold_master
Create Date: 2026-02-24

content is editor-only (TipTap JSON); template_html is source of truth for rendering.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision: str = "033_content_nullable"
down_revision: Union[str, None] = "032_po_gold_master"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    # Backfill null/empty to '{}' before altering (safety for any edge-case nulls)
    conn.execute(text("UPDATE document_templates SET content = '{}' WHERE content IS NULL"))
    op.alter_column(
        "document_templates",
        "content",
        nullable=True,
        server_default=sa.text("'{}'"),
        existing_type=sa.Text(),
        existing_nullable=False,
        existing_server_default=sa.text("''"),
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(text("UPDATE document_templates SET content = '' WHERE content IS NULL OR content = '{}'"))
    op.alter_column(
        "document_templates",
        "content",
        nullable=False,
        server_default=sa.text("''"),
        existing_type=sa.Text(),
        existing_nullable=True,
    )
