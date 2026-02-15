"""Backfill job_id: create one Job per quote and per purchase_order that has no job_id.

Revision ID: 005_backfill_job
Revises: 004_core_packing
Create Date: 2025-02-08

"""
import uuid
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "005_backfill_job"
down_revision: Union[str, None] = "004_core_packing"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _next_job_no(conn) -> int:
    r = conn.execute(text("SELECT next_val FROM job_no_sequence WHERE name = 'default' FOR UPDATE")).fetchone()
    if not r:
        conn.execute(text("INSERT INTO job_no_sequence (name, next_val) VALUES ('default', 1) ON CONFLICT (name) DO NOTHING"))
        r = conn.execute(text("SELECT next_val FROM job_no_sequence WHERE name = 'default'")).fetchone()
    num = int(r[0]) if r else 1
    conn.execute(text("UPDATE job_no_sequence SET next_val = :n WHERE name = 'default'"), {"n": num + 1})
    return num


def upgrade() -> None:
    conn = op.get_bind()
    prefix = "J"
    quotes = conn.execute(text("SELECT id, customer_id, quote_number FROM quotes WHERE job_id IS NULL")).fetchall()
    for q in quotes:
        qid, customer_id, quote_number = q[0], q[1], q[2]
        num = _next_job_no(conn)
        job_no = f"{prefix}{num:04d}"
        job_id = str(uuid.uuid4())
        conn.execute(
            text("INSERT INTO jobs (id, job_no, customer_id, title, status) VALUES (:id, :job_no, :customer_id, :title, 'open')"),
            {"id": job_id, "job_no": job_no, "customer_id": customer_id, "title": f"Quote {quote_number}"},
        )
        conn.execute(text("UPDATE quotes SET job_id = :jid WHERE id = :qid"), {"jid": job_id, "qid": qid})
    pos = conn.execute(text("SELECT id, po_number FROM purchase_orders WHERE job_id IS NULL")).fetchall()
    for po in pos:
        poid, po_number = po[0], po[1]
        num = _next_job_no(conn)
        job_no = f"{prefix}{num:04d}"
        job_id = str(uuid.uuid4())
        conn.execute(
            text("INSERT INTO jobs (id, job_no, customer_id, title, status) VALUES (:id, :job_no, NULL, :title, 'open')"),
            {"id": job_id, "job_no": job_no, "title": f"PO {po_number or 'Draft'}"},
        )
        conn.execute(text("UPDATE purchase_orders SET job_id = :jid WHERE id = :poid"), {"jid": job_id, "poid": poid})


def downgrade() -> None:
    op.execute(text("UPDATE quotes SET job_id = NULL"))
    op.execute(text("UPDATE purchase_orders SET job_id = NULL"))