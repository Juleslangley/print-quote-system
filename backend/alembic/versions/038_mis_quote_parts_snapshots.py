"""MIS-style quotation: quote job_type/name, quote_parts, quote_price_snapshots.

Revision ID: 038_mis_parts
Revises: 037_job_type_routing
Create Date: 2026-02-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision: str = "038_mis_parts"
down_revision: Union[str, None] = "037_job_type_routing"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    ts = sa.DateTime(timezone=True)
    default_ts = sa.text("now()")

    # Add job_type and name to quotes (MIS flow)
    op.add_column("quotes", sa.Column("job_type", sa.String(64), nullable=True))
    op.add_column("quotes", sa.Column("name", sa.String(256), nullable=True, server_default=""))

    # quote_parts: MIS-style parts (material_id, finished W/H, qty, sides, overrides)
    op.create_table(
        "quote_parts",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("quote_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False, server_default=""),
        sa.Column("material_id", sa.String(), nullable=True),
        sa.Column("finished_w_mm", sa.Integer(), nullable=True),
        sa.Column("finished_h_mm", sa.Integer(), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("sides", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("preferred_sheet_size_id", sa.String(), nullable=True),
        sa.Column("waste_pct_override", sa.Float(), nullable=True),
        sa.Column("setup_minutes_override", sa.Float(), nullable=True),
        sa.Column("machine_key_override", sa.String(), nullable=True),
        sa.Column("created_at", ts, server_default=default_ts, nullable=True),
        sa.Column("updated_at", ts, server_default=default_ts, nullable=True),
        sa.ForeignKeyConstraint(["quote_id"], ["quotes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["material_id"], ["materials.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["preferred_sheet_size_id"], ["material_sizes.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_quote_parts_quote_id", "quote_parts", ["quote_id"])
    op.create_index("ix_quote_parts_material_id", "quote_parts", ["material_id"])

    # quote_price_snapshots: locked revisions with input_hash (no-op lock prevention)
    op.create_table(
        "quote_price_snapshots",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("quote_id", sa.String(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("pricing_version", sa.String(), nullable=False),
        sa.Column("input_hash", sa.String(64), nullable=False),
        sa.Column("result_json", JSONB, nullable=False),
        sa.Column("created_at", ts, server_default=default_ts, nullable=True),
        sa.ForeignKeyConstraint(["quote_id"], ["quotes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_quote_price_snapshots_quote_id", "quote_price_snapshots", ["quote_id"])
    op.create_index("ix_quote_price_snapshots_input_hash", "quote_price_snapshots", ["input_hash"])


def downgrade() -> None:
    op.drop_index("ix_quote_price_snapshots_input_hash", table_name="quote_price_snapshots")
    op.drop_index("ix_quote_price_snapshots_quote_id", table_name="quote_price_snapshots")
    op.drop_table("quote_price_snapshots")
    op.drop_index("ix_quote_parts_material_id", table_name="quote_parts")
    op.drop_index("ix_quote_parts_quote_id", table_name="quote_parts")
    op.drop_table("quote_parts")
    op.drop_column("quotes", "name")
    op.drop_column("quotes", "job_type")
