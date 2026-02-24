"""Change document_renders template_id FK to CASCADE for easier cleanup.

Revision ID: 035_renders_cascade
Revises: 034_template_versioning
Create Date: 2026-02-24

When a document_template is deleted, its document_renders are cascade-deleted.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "035_renders_cascade"
down_revision: Union[str, None] = "034_template_versioning"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "document_renders_template_id_fkey",
        "document_renders",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "document_renders_template_id_fkey",
        "document_renders",
        "document_templates",
        ["template_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint(
        "document_renders_template_id_fkey",
        "document_renders",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "document_renders_template_id_fkey",
        "document_renders",
        "document_templates",
        ["template_id"],
        ["id"],
        ondelete="RESTRICT",
    )
