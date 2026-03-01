"""Add jobs.job_type for production routing defaults.

Revision ID: 037_job_type_routing
Revises: 036_repair_po_lines
Create Date: 2026-02-23
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "037_job_type_routing"
down_revision: Union[str, None] = "036_repair_po_lines"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "jobs",
        sa.Column(
            "job_type",
            sa.String(length=64),
            nullable=False,
            server_default="LARGE_FORMAT_SHEET",
        ),
    )
    op.create_index("ix_jobs_job_type", "jobs", ["job_type"])


def downgrade() -> None:
    op.drop_index("ix_jobs_job_type", table_name="jobs")
    op.drop_column("jobs", "job_type")

