"""JobType per PART (required). default_job_type on Quote for UI only.

Revision ID: 039_part_job_type
Revises: 038_mis_parts
Create Date: 2026-02-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "039_part_job_type"
down_revision: Union[str, None] = "038_mis_parts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # quote_parts: add job_type (nullable first, backfill, then NOT NULL)
    op.add_column("quote_parts", sa.Column("job_type", sa.String(32), nullable=True))
    op.execute(sa.text("UPDATE quote_parts SET job_type = 'LARGE_FORMAT_SHEET' WHERE job_type IS NULL"))
    op.alter_column(
        "quote_parts",
        "job_type",
        existing_type=sa.String(32),
        nullable=False,
        existing_nullable=True,
    )
    op.create_index("ix_quote_parts_job_type", "quote_parts", ["job_type"])

    # Quote: rename job_type -> default_job_type (optional, UI convenience only)
    op.add_column("quotes", sa.Column("default_job_type", sa.String(64), nullable=True))
    op.execute(sa.text("UPDATE quotes SET default_job_type = job_type WHERE job_type IS NOT NULL"))
    op.execute(sa.text("DROP INDEX IF EXISTS ix_quotes_job_type"))
    op.drop_column("quotes", "job_type")


def downgrade() -> None:
    op.add_column("quotes", sa.Column("job_type", sa.String(64), nullable=True))
    op.execute(sa.text("UPDATE quotes SET job_type = default_job_type WHERE default_job_type IS NOT NULL"))
    op.drop_column("quotes", "default_job_type")
    op.create_index("ix_quotes_job_type", "quotes", ["job_type"], unique=False)

    op.drop_index("ix_quote_parts_job_type", table_name="quote_parts")
    op.drop_column("quote_parts", "job_type")
