"""Add template_version_id and render_hash to document_renders for render cache.

Revision ID: 030_render_cache
Revises: 029_po_dom_order
Create Date: 2026-02-24

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "030_render_cache"
down_revision: Union[str, None] = "029_po_dom_order"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("document_renders", sa.Column("template_version_id", sa.String(64), nullable=True))
    op.add_column("document_renders", sa.Column("render_hash", sa.String(64), nullable=True))
    op.create_index(
        "ix_document_renders_cache_lookup",
        "document_renders",
        ["doc_type", "entity_id", "template_version_id", "render_hash"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_document_renders_cache_lookup", table_name="document_renders")
    op.drop_column("document_renders", "render_hash")
    op.drop_column("document_renders", "template_version_id")
