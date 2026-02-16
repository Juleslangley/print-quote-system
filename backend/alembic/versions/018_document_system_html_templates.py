"""Add document_templates + document_renders for HTML→PDF documents.

Revision ID: 018_document_system_html_templates
Revises: 017_drop_document_templates
Create Date: 2026-02-16
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "018_doc_system_html"
down_revision: Union[str, None] = "017_drop_document_templates"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(conn, name: str) -> bool:
    from sqlalchemy import inspect
    return name in inspect(conn).get_table_names()


def upgrade() -> None:
    conn = op.get_bind()

    if not _table_exists(conn, "document_templates"):
        op.create_table(
            "document_templates",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("doc_type", sa.String(), nullable=False),
            sa.Column("name", sa.String(), nullable=False, server_default=""),
            sa.Column("engine", sa.String(), nullable=False, server_default="html_jinja"),
            sa.Column("content", sa.Text(), nullable=False, server_default=""),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_document_templates_doc_type", "document_templates", ["doc_type"], unique=False)
        op.create_index("ix_document_templates_doc_type_is_active", "document_templates", ["doc_type", "is_active"], unique=False)

        # Enforce: only one active template per doc_type (Postgres only).
        try:
            op.create_index(
                "ux_document_templates_one_active_per_type",
                "document_templates",
                ["doc_type"],
                unique=True,
                postgresql_where=sa.text("is_active IS TRUE"),
            )
        except Exception:
            # Non-Postgres dialects may not support partial indexes; app-layer enforcement still applies.
            pass

    if not _table_exists(conn, "document_renders"):
        op.create_table(
            "document_renders",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("doc_type", sa.String(), nullable=False),
            sa.Column("entity_id", sa.String(), nullable=False),
            sa.Column("template_id", sa.String(), nullable=False),
            sa.Column("file_id", sa.String(), nullable=False),
            sa.Column("created_by_user_id", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.ForeignKeyConstraint(["template_id"], ["document_templates.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["file_id"], ["files.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_document_renders_doc_type", "document_renders", ["doc_type"], unique=False)
        op.create_index("ix_document_renders_entity_id", "document_renders", ["entity_id"], unique=False)
        op.create_index("ix_document_renders_template_id", "document_renders", ["template_id"], unique=False)
        op.create_index("ix_document_renders_file_id", "document_renders", ["file_id"], unique=False)
        op.create_index("ix_document_renders_created_by_user_id", "document_renders", ["created_by_user_id"], unique=False)
        op.create_index("ix_document_renders_doc_type_entity_id", "document_renders", ["doc_type", "entity_id"], unique=False)


def downgrade() -> None:
    conn = op.get_bind()
    if _table_exists(conn, "document_renders"):
        for idx in (
            "ix_document_renders_doc_type_entity_id",
            "ix_document_renders_created_by_user_id",
            "ix_document_renders_file_id",
            "ix_document_renders_template_id",
            "ix_document_renders_entity_id",
            "ix_document_renders_doc_type",
        ):
            try:
                op.drop_index(idx, table_name="document_renders")
            except Exception:
                pass
        op.drop_table("document_renders")

    if _table_exists(conn, "document_templates"):
        for idx in (
            "ux_document_templates_one_active_per_type",
            "ix_document_templates_doc_type_is_active",
            "ix_document_templates_doc_type",
        ):
            try:
                op.drop_index(idx, table_name="document_templates")
            except Exception:
                pass
        op.drop_table("document_templates")

