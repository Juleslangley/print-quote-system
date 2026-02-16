"""Drop document_templates table (remove admin documents templates feature).

Revision ID: 017_drop_document_templates
Revises: 016_document_templates
Create Date: 2026-02-16
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "017_drop_document_templates"
down_revision: Union[str, None] = "016_document_templates"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(conn, name: str) -> bool:
    from sqlalchemy import inspect
    return name in inspect(conn).get_table_names()


def upgrade() -> None:
    conn = op.get_bind()
    if not _table_exists(conn, "document_templates"):
        return
    # indexes were created in 016; drop table will cascade indexes in Postgres, but we drop explicitly for safety
    try:
        op.drop_index(op.f("ix_document_templates_file_id"), table_name="document_templates")
    except Exception:
        pass
    try:
        op.drop_index(op.f("ix_document_templates_doc_type"), table_name="document_templates")
    except Exception:
        pass
    op.drop_table("document_templates")


def downgrade() -> None:
    # Recreate the table exactly as 016 did.
    op.create_table(
        "document_templates",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("doc_type", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=True, server_default=""),
        sa.Column("active", sa.Boolean(), nullable=True, server_default="true"),
        sa.Column("file_id", sa.String(), nullable=True),
        sa.Column("filename", sa.String(), nullable=True, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["file_id"], ["files.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_document_templates_doc_type"), "document_templates", ["doc_type"], unique=True)
    op.create_index(op.f("ix_document_templates_file_id"), "document_templates", ["file_id"], unique=False)

