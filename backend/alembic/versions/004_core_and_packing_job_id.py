"""Core tables (jobs, job_versions, files, file_links, events_outbox), packing tables, job_id on quotes/po

Revision ID: 004_core_packing
Revises: 003_mat_supplier
Create Date: 2025-02-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision: str = "004_core_packing"
down_revision: Union[str, None] = "003_mat_supplier"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(conn, name: str) -> bool:
    from sqlalchemy import inspect
    return name in inspect(conn).get_table_names()


def upgrade() -> None:
    conn = op.get_bind()
    # --- Job number sequence (one row: name='default', next_val) ---
    if not _table_exists(conn, "job_no_sequence"):
        op.create_table(
            "job_no_sequence",
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("next_val", sa.Integer(), nullable=True, server_default="1"),
            sa.PrimaryKeyConstraint("name"),
        )
    op.execute(sa.text("INSERT INTO job_no_sequence (name, next_val) VALUES ('default', 1) ON CONFLICT (name) DO NOTHING"))

    # --- Core: jobs ---
    if not _table_exists(conn, "jobs"):
        op.create_table(
            "jobs",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("job_no", sa.String(), nullable=False),
            sa.Column("customer_id", sa.String(), nullable=True),
            sa.Column("title", sa.String(), nullable=True, server_default=""),
            sa.Column("status", sa.String(), nullable=True, server_default="open"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_jobs_job_no"), "jobs", ["job_no"], unique=True)
        op.create_index(op.f("ix_jobs_customer_id"), "jobs", ["customer_id"], unique=False)
        op.create_index(op.f("ix_jobs_status"), "jobs", ["status"], unique=False)

    # --- Core: job_versions ---
    if not _table_exists(conn, "job_versions"):
        op.create_table(
            "job_versions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("job_id", sa.String(), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("snapshot_json", JSONB, nullable=True, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_job_versions_job_id"), "job_versions", ["job_id"], unique=False)

    # --- Core: files ---
    if not _table_exists(conn, "files"):
        op.create_table(
            "files",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("storage_key", sa.String(), nullable=False),
            sa.Column("mime", sa.String(), nullable=True, server_default="application/octet-stream"),
            sa.Column("size", sa.Integer(), nullable=True, server_default="0"),
            sa.Column("sha256", sa.String(), nullable=True, server_default=""),
            sa.Column("uploaded_by", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_files_storage_key"), "files", ["storage_key"], unique=True)
        op.create_index(op.f("ix_files_uploaded_by"), "files", ["uploaded_by"], unique=False)

    # --- Core: file_links ---
    if not _table_exists(conn, "file_links"):
        op.create_table(
            "file_links",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("file_id", sa.String(), nullable=False),
            sa.Column("entity_type", sa.String(), nullable=False),
            sa.Column("entity_id", sa.String(), nullable=False),
            sa.Column("tag", sa.String(), nullable=True, server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.ForeignKeyConstraint(["file_id"], ["files.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_file_links_file_id"), "file_links", ["file_id"], unique=False)
        op.create_index(op.f("ix_file_links_entity_type"), "file_links", ["entity_type"], unique=False)
        op.create_index(op.f("ix_file_links_entity_id"), "file_links", ["entity_id"], unique=False)
        op.create_index(op.f("ix_file_links_tag"), "file_links", ["tag"], unique=False)

    # --- Core: events_outbox ---
    if not _table_exists(conn, "events_outbox"):
        op.create_table(
            "events_outbox",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("event_type", sa.String(), nullable=False),
            sa.Column("payload", JSONB, nullable=True, server_default="{}"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_events_outbox_event_type"), "events_outbox", ["event_type"], unique=False)

    # --- Packing: packing_batches ---
    if not _table_exists(conn, "packing_batches"):
        op.create_table(
            "packing_batches",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("job_id", sa.String(), nullable=False),
            sa.Column("name", sa.String(), nullable=True, server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_packing_batches_job_id"), "packing_batches", ["job_id"], unique=False)

    # --- Packing: packing_store_jobs ---
    if not _table_exists(conn, "packing_store_jobs"):
        op.create_table(
            "packing_store_jobs",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("batch_id", sa.String(), nullable=False),
            sa.Column("store_name", sa.String(), nullable=False),
            sa.Column("status", sa.String(), nullable=True, server_default="pending"),
            sa.Column("box_count", sa.Integer(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("packed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.ForeignKeyConstraint(["batch_id"], ["packing_batches.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_packing_store_jobs_batch_id"), "packing_store_jobs", ["batch_id"], unique=False)
        op.create_index(op.f("ix_packing_store_jobs_store_name"), "packing_store_jobs", ["store_name"], unique=False)
        op.create_index(op.f("ix_packing_store_jobs_status"), "packing_store_jobs", ["status"], unique=False)

    # --- Packing: packing_store_line_items ---
    if not _table_exists(conn, "packing_store_line_items"):
        op.create_table(
            "packing_store_line_items",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("store_job_id", sa.String(), nullable=False),
            sa.Column("component", sa.String(), nullable=True, server_default=""),
            sa.Column("description", sa.String(), nullable=True, server_default=""),
            sa.Column("qty", sa.Integer(), nullable=True, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.ForeignKeyConstraint(["store_job_id"], ["packing_store_jobs.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_packing_store_line_items_store_job_id"), "packing_store_line_items", ["store_job_id"], unique=False)

    # --- Add job_id to quotes and purchase_orders (idempotent) ---
    op.execute(sa.text("ALTER TABLE quotes ADD COLUMN IF NOT EXISTS job_id VARCHAR REFERENCES jobs(id) ON DELETE SET NULL"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_quotes_job_id ON quotes (job_id)"))

    op.execute(sa.text("ALTER TABLE purchase_orders ADD COLUMN IF NOT EXISTS job_id VARCHAR REFERENCES jobs(id) ON DELETE SET NULL"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_purchase_orders_job_id ON purchase_orders (job_id)"))


def downgrade() -> None:
    op.drop_index(op.f("ix_purchase_orders_job_id"), table_name="purchase_orders")
    op.drop_constraint("fk_purchase_orders_job_id", "purchase_orders", type_="foreignkey")
    op.drop_column("purchase_orders", "job_id")

    op.drop_index(op.f("ix_quotes_job_id"), table_name="quotes")
    op.drop_constraint("fk_quotes_job_id", "quotes", type_="foreignkey")
    op.drop_column("quotes", "job_id")

    op.drop_index(op.f("ix_packing_store_line_items_store_job_id"), table_name="packing_store_line_items")
    op.drop_table("packing_store_line_items")
    op.drop_index(op.f("ix_packing_store_jobs_status"), table_name="packing_store_jobs")
    op.drop_index(op.f("ix_packing_store_jobs_store_name"), table_name="packing_store_jobs")
    op.drop_index(op.f("ix_packing_store_jobs_batch_id"), table_name="packing_store_jobs")
    op.drop_table("packing_store_jobs")
    op.drop_index(op.f("ix_packing_batches_job_id"), table_name="packing_batches")
    op.drop_table("packing_batches")
    op.drop_index(op.f("ix_events_outbox_event_type"), table_name="events_outbox")
    op.drop_table("events_outbox")
    op.drop_index(op.f("ix_file_links_tag"), table_name="file_links")
    op.drop_index(op.f("ix_file_links_entity_id"), table_name="file_links")
    op.drop_index(op.f("ix_file_links_entity_type"), table_name="file_links")
    op.drop_index(op.f("ix_file_links_file_id"), table_name="file_links")
    op.drop_table("file_links")
    op.drop_index(op.f("ix_files_uploaded_by"), table_name="files")
    op.drop_index(op.f("ix_files_storage_key"), table_name="files")
    op.drop_table("files")
    op.drop_index(op.f("ix_job_versions_job_id"), table_name="job_versions")
    op.drop_table("job_versions")
    op.drop_index(op.f("ix_jobs_status"), table_name="jobs")
    op.drop_index(op.f("ix_jobs_customer_id"), table_name="jobs")
    op.drop_index(op.f("ix_jobs_job_no"), table_name="jobs")
    op.drop_table("jobs")
    op.drop_table("job_no_sequence")
