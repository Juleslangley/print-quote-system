"""Ensure machines.active is NOT NULL with default true (soft-deactivation support).

Revision ID: 040_machines_active
Revises: 039_part_job_type
Create Date: 2026-02-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "040_machines_active"
down_revision: Union[str, None] = "039_part_job_type"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(sa.text("UPDATE machines SET active = true WHERE active IS NULL"))
    op.alter_column(
        "machines",
        "active",
        existing_type=sa.Boolean(),
        nullable=False,
        server_default=sa.text("true"),
    )


def downgrade() -> None:
    op.alter_column(
        "machines",
        "active",
        existing_type=sa.Boolean(),
        nullable=True,
        server_default=sa.text("true"),
    )
