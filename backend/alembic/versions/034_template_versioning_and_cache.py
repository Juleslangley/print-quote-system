"""Add version_num, created_by to document_template_versions; current_version_id to document_templates.

Revision ID: 034_template_versioning
Revises: 033_content_nullable
Create Date: 2026-02-24

Stable template versioning and render cache: version_num increments on save,
current_version_id points to latest version.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision: str = "034_template_versioning"
down_revision: Union[str, None] = "033_content_nullable"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # document_template_versions: version_num, created_by
    op.add_column(
        "document_template_versions",
        sa.Column("version_num", sa.Integer(), nullable=True),
    )
    op.add_column(
        "document_template_versions",
        sa.Column("created_by", sa.String(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    # Backfill version_num: assign 1, 2, 3... per template_id order by created_at
    conn.execute(text("""
        WITH ordered AS (
            SELECT id, template_id, created_at,
                   ROW_NUMBER() OVER (PARTITION BY template_id ORDER BY created_at ASC NULLS LAST) AS rn
            FROM document_template_versions
        )
        UPDATE document_template_versions v
        SET version_num = o.rn
        FROM ordered o WHERE v.id = o.id
    """))
    op.alter_column(
        "document_template_versions",
        "version_num",
        nullable=False,
    )
    op.create_index(
        "ix_document_template_versions_template_version",
        "document_template_versions",
        ["template_id", "version_num"],
        unique=False,
    )

    # document_templates: current_version_id
    op.add_column(
        "document_templates",
        sa.Column("current_version_id", sa.String(), nullable=True),
    )
    # Backfill: set current_version_id to latest version per template
    conn.execute(text("""
        UPDATE document_templates t
        SET current_version_id = (
            SELECT v.id FROM document_template_versions v
            WHERE v.template_id = t.id
            ORDER BY v.version_num DESC NULLS LAST
            LIMIT 1
        )
    """))
    op.create_foreign_key(
        "fk_document_templates_current_version",
        "document_templates",
        "document_template_versions",
        ["current_version_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_document_templates_current_version",
        "document_templates",
        type_="foreignkey",
    )
    op.drop_column("document_templates", "current_version_id")
    op.drop_index(
        "ix_document_template_versions_template_version",
        table_name="document_template_versions",
    )
    op.drop_column("document_template_versions", "created_by")
    op.drop_column("document_template_versions", "version_num")
