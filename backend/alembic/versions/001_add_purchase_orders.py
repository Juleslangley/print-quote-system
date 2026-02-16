"""add purchase orders

Revision ID: 001_add_po
Revises:
Create Date: 2025-02-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "001_add_po"
down_revision: Union[str, None] = "000_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "purchase_orders",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("po_number", sa.String(), nullable=True),
        sa.Column("supplier_id", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True, server_default="draft"),
        sa.Column("currency", sa.String(), nullable=True, server_default="GBP"),
        sa.Column("order_date", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("required_by", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expected_by", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivery_name", sa.String(), nullable=True, server_default=""),
        sa.Column("delivery_address", sa.String(), nullable=True, server_default=""),
        sa.Column("notes", sa.String(), nullable=True, server_default=""),
        sa.Column("internal_notes", sa.String(), nullable=True, server_default=""),
        sa.Column("subtotal_gbp", sa.Float(), nullable=True, server_default="0"),
        sa.Column("vat_gbp", sa.Float(), nullable=True, server_default="0"),
        sa.Column("total_gbp", sa.Float(), nullable=True, server_default="0"),
        sa.Column("created_by_user_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"], ondelete="RESTRICT"),
    )
    op.create_index(op.f("ix_purchase_orders_po_number"), "purchase_orders", ["po_number"], unique=True)
    op.create_index(op.f("ix_purchase_orders_supplier_id"), "purchase_orders", ["supplier_id"], unique=False)
    op.create_index(op.f("ix_purchase_orders_created_by_user_id"), "purchase_orders", ["created_by_user_id"], unique=False)
    op.create_table(
        "purchase_order_lines",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("po_id", sa.BigInteger(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("material_id", sa.String(), nullable=True),
        sa.Column("material_size_id", sa.String(), nullable=True),
        sa.Column("description", sa.String(), nullable=True, server_default=""),
        sa.Column("supplier_product_code", sa.String(), nullable=True, server_default=""),
        sa.Column("qty", sa.Float(), nullable=True, server_default="0"),
        sa.Column("uom", sa.String(), nullable=True, server_default="sheet"),
        sa.Column("unit_cost_gbp", sa.Float(), nullable=True, server_default="0"),
        sa.Column("line_total_gbp", sa.Float(), nullable=True, server_default="0"),
        sa.Column("received_qty", sa.Float(), nullable=True, server_default="0"),
        sa.Column("active", sa.Boolean(), nullable=True, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["material_id"], ["materials.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["material_size_id"], ["material_sizes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["po_id"], ["purchase_orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_purchase_order_lines_po_id"), "purchase_order_lines", ["po_id"], unique=False)
    op.create_index(op.f("ix_purchase_order_lines_material_id"), "purchase_order_lines", ["material_id"], unique=False)
    op.create_index(op.f("ix_purchase_order_lines_material_size_id"), "purchase_order_lines", ["material_size_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_purchase_order_lines_material_size_id"), table_name="purchase_order_lines")
    op.drop_index(op.f("ix_purchase_order_lines_material_id"), table_name="purchase_order_lines")
    op.drop_index(op.f("ix_purchase_order_lines_po_id"), table_name="purchase_order_lines")
    op.drop_table("purchase_order_lines")
    op.drop_index(op.f("ix_purchase_orders_created_by_user_id"), table_name="purchase_orders")
    op.drop_index(op.f("ix_purchase_orders_supplier_id"), table_name="purchase_orders")
    op.drop_index(op.f("ix_purchase_orders_po_number"), table_name="purchase_orders")
    op.drop_table("purchase_orders")
