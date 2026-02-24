"""Add template_html, template_json, template_css and document_template_versions.

Revision ID: 019_doc_tpl_wysiwyg
Revises: 018_doc_system_html
Create Date: 2026-02-23

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "019_doc_tpl_wysiwyg"
down_revision: Union[str, None] = "018_doc_system_html"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "document_templates",
        sa.Column("template_html", sa.Text(), nullable=True),
    )
    op.add_column(
        "document_templates",
        sa.Column("template_json", sa.Text(), nullable=True),
    )
    op.add_column(
        "document_templates",
        sa.Column("template_css", sa.Text(), nullable=True),
    )

    op.create_table(
        "document_template_versions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("template_id", sa.String(), nullable=False),
        sa.Column("template_html", sa.Text(), nullable=True),
        sa.Column("template_json", sa.Text(), nullable=True),
        sa.Column("template_css", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["template_id"], ["document_templates.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_document_template_versions_template_id",
        "document_template_versions",
        ["template_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_document_template_versions_template_id", table_name="document_template_versions")
    op.drop_table("document_template_versions")
    op.drop_column("document_templates", "template_css")
    op.drop_column("document_templates", "template_json")
    op.drop_column("document_templates", "template_html")
