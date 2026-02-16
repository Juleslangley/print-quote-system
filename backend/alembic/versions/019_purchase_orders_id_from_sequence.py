"""Purchase orders: use Integer id, po_number from id; drop purchase_orders_seq.

Revision ID: 019_po_id_from_seq
Revises: 018_document_system_html_templates
Create Date: 2026-02-16

- Migrates purchase_orders.id from String (UUID) to Integer (BIGSERIAL).
- Sets po_number = 'PO' + zero-padded 7 digits from id.
- Drops sequence purchase_orders_seq.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


revision: str = "019_po_id_from_seq"
down_revision: Union[str, None] = "018_document_system_html_templates"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # 1) Create purchase_orders_new with Integer id and identity
    op.create_table(
        "purchase_orders_new",
        sa.Column("id", sa.BigInteger(), sa.Identity(start=1, increment=1), primary_key=True),
        sa.Column("po_number", sa.String(), nullable=True),
        sa.Column("job_id", sa.String(), sa.ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("supplier_id", sa.String(), sa.ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("status", sa.String(), server_default="draft", nullable=True),
        sa.Column("currency", sa.String(), server_default="GBP", nullable=True),
        sa.Column("order_date", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("required_by", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expected_by", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivery_name", sa.String(), server_default="", nullable=True),
        sa.Column("delivery_address", sa.String(), server_default="", nullable=True),
        sa.Column("notes", sa.String(), server_default="", nullable=True),
        sa.Column("internal_notes", sa.String(), server_default="", nullable=True),
        sa.Column("subtotal_gbp", sa.Float(), server_default="0", nullable=True),
        sa.Column("vat_gbp", sa.Float(), server_default="0", nullable=True),
        sa.Column("total_gbp", sa.Float(), server_default="0", nullable=True),
        sa.Column("created_by_user_id", sa.String(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
    )
    op.create_index("ix_purchase_orders_new_po_number", "purchase_orders_new", ["po_number"], unique=True)
    op.create_index("ix_purchase_orders_new_supplier_id", "purchase_orders_new", ["supplier_id"], unique=False)
    op.create_index("ix_purchase_orders_new_job_id", "purchase_orders_new", ["job_id"], unique=False)
    op.create_index("ix_purchase_orders_new_created_by_user_id", "purchase_orders_new", ["created_by_user_id"], unique=False)

    # 2) Copy data: insert and capture old_id -> new_id mapping via temp column
    conn.execute(text("""
        INSERT INTO purchase_orders_new (
            po_number, job_id, supplier_id, status, currency, order_date,
            required_by, expected_by, delivery_name, delivery_address, notes, internal_notes,
            subtotal_gbp, vat_gbp, total_gbp, created_by_user_id, created_at, updated_at
        )
        SELECT
            po_number, job_id, supplier_id, status, currency, order_date,
            required_by, expected_by, delivery_name, delivery_address, notes, internal_notes,
            subtotal_gbp, vat_gbp, total_gbp, created_by_user_id, created_at, updated_at
        FROM purchase_orders
        ORDER BY created_at NULLS LAST, id
    """))

    # 3) Update po_number = PO{id:07d} for all rows in new table
    conn.execute(text("""
        UPDATE purchase_orders_new
        SET po_number = 'PO' || LPAD(id::text, 7, '0')
    """))

    # 4) Add old_id to purchase_orders_new for mapping (populate via order match)
    # We need old_id in purchase_orders_new to join. Add col, then update from a temp that has order.
    op.add_column("purchase_orders_new", sa.Column("old_id", sa.String(), nullable=True))
    # Match by (created_at, supplier_id, status, ...) since we inserted in same order
    conn.execute(text("""
        WITH ordered_old AS (
            SELECT id as old_id, ROW_NUMBER() OVER (ORDER BY created_at NULLS LAST, id) as rn
            FROM purchase_orders
        ),
        ordered_new AS (
            SELECT id as new_id, ROW_NUMBER() OVER (ORDER BY id) as rn
            FROM purchase_orders_new
        )
        UPDATE purchase_orders_new pn
        SET old_id = oo.old_id
        FROM ordered_old oo
        JOIN ordered_new ord_new ON ord_new.rn = oo.rn
        WHERE pn.id = ord_new.new_id
    """))

    # 5) Add po_id_new to purchase_order_lines
    op.add_column("purchase_order_lines", sa.Column("po_id_new", sa.BigInteger(), nullable=True))
    conn.execute(text("""
        UPDATE purchase_order_lines pol
        SET po_id_new = pn.id
        FROM purchase_orders_new pn
        WHERE pol.po_id = pn.old_id
    """))

    # 6) Update document_renders entity_id where doc_type = 'purchase_order'
    conn.execute(text("""
        UPDATE document_renders dr
        SET entity_id = pn.id::text
        FROM purchase_orders_new pn
        WHERE dr.doc_type = 'purchase_order' AND dr.entity_id = pn.old_id
    """))

    # 7) Drop FK from purchase_order_lines to purchase_orders
    op.drop_constraint("purchase_order_lines_po_id_fkey", "purchase_order_lines", type_="foreignkey")

    # 8) Drop old po_id, rename po_id_new to po_id
    op.drop_index("ix_purchase_order_lines_po_id", table_name="purchase_order_lines")
    op.drop_column("purchase_order_lines", "po_id")
    op.alter_column(
        "purchase_order_lines",
        "po_id_new",
        new_column_name="po_id",
        nullable=False,
    )
    op.create_foreign_key(
        "purchase_order_lines_po_id_fkey",
        "purchase_order_lines",
        "purchase_orders_new",
        ["po_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_purchase_order_lines_po_id", "purchase_order_lines", ["po_id"], unique=False)

    # 9) Drop old purchase_orders, rename purchase_orders_new
    op.drop_index("ix_purchase_orders_created_by_user_id", table_name="purchase_orders")
    op.drop_index("ix_purchase_orders_supplier_id", table_name="purchase_orders")
    op.drop_index("ix_purchase_orders_po_number", table_name="purchase_orders")
    op.drop_index("ix_purchase_orders_job_id", table_name="purchase_orders")
    op.drop_table("purchase_orders")

    op.rename_table("purchase_orders_new", "purchase_orders")

    # 10) Drop old_id column (Postgres automatically updates FK target when table is renamed)
    op.drop_column("purchase_orders", "old_id")

    # 11) Rename indexes to match standard naming (ix_purchase_orders_*)
    op.drop_index("ix_purchase_orders_new_po_number", table_name="purchase_orders")
    op.drop_index("ix_purchase_orders_new_supplier_id", table_name="purchase_orders")
    op.drop_index("ix_purchase_orders_new_job_id", table_name="purchase_orders")
    op.drop_index("ix_purchase_orders_new_created_by_user_id", table_name="purchase_orders")
    op.create_index("ix_purchase_orders_po_number", "purchase_orders", ["po_number"], unique=True)
    op.create_index("ix_purchase_orders_supplier_id", "purchase_orders", ["supplier_id"], unique=False)
    op.create_index("ix_purchase_orders_job_id", "purchase_orders", ["job_id"], unique=False)
    op.create_index("ix_purchase_orders_created_by_user_id", "purchase_orders", ["created_by_user_id"], unique=False)

    # 12) Drop sequence purchase_orders_seq
    conn.execute(text("DROP SEQUENCE IF EXISTS purchase_orders_seq CASCADE"))


def downgrade() -> None:
    conn = op.get_bind()

    # Recreate sequence
    conn.execute(text("CREATE SEQUENCE IF NOT EXISTS purchase_orders_seq START 1"))

    # Downgrade is complex (would need to reverse the migration with a new string-id table)
    # For simplicity, raise - full downgrade would require restoring from backup
    raise NotImplementedError(
        "Downgrade from 019 (Integer id) to String id is not supported. Restore from backup if needed."
    )
