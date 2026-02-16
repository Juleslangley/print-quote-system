"""Regression test: prevent reintroduction of purchase_orders_seq.

po_number must derive from purchase_orders.id (BigInteger autoincrement), never
from a separate purchase_orders_seq sequence.
"""
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import app
from app.api.permissions import require_admin, require_sales
from app.models.supplier import Supplier


SEQ_GUARD_MSG = (
    "purchase_orders_seq must never exist; po_number must derive from id sequence."
)


@pytest.fixture
def app_with_auth_bypass():
    """Override auth so we can call create without real login."""
    app.dependency_overrides[require_admin] = lambda: None
    app.dependency_overrides[require_sales] = lambda: None
    try:
        yield app
    finally:
        app.dependency_overrides.pop(require_admin, None)
        app.dependency_overrides.pop(require_sales, None)


def test_create_po_response_and_no_purchase_orders_seq(
    app_with_auth_bypass, use_test_db, test_engine
):
    """
    Create a PO via API; assert response ok and po_number format.
    Assert purchase_orders_seq does NOT exist in the database.
    """
    from app.core.db import SessionLocal

    db = SessionLocal()
    try:
        supplier = db.query(Supplier).first()
        if not supplier:
            pytest.skip("No supplier in DB; run POST /api/seed/dev first")
        supplier_id = supplier.id
    finally:
        db.close()

    client = TestClient(app_with_auth_bypass)
    resp = client.post(
        "/api/purchase-orders",
        json={"supplier_id": supplier_id},
    )
    assert resp.status_code in (200, 201), resp.json()
    data = resp.json()
    assert "po_number" in data, data
    assert data["po_number"], "po_number must not be empty"
    assert str(data["po_number"]).startswith("PO"), (
        f"po_number must start with 'PO', got: {data['po_number']}"
    )

    # Only Postgres has pg_class; skip sequence check on SQLite
    url = str(test_engine.url)
    if "sqlite" in url.lower():
        return

    with test_engine.connect() as conn:
        result = conn.execute(
            text(
                "SELECT relname FROM pg_class "
                "WHERE relkind = 'S' AND relname = 'purchase_orders_seq'"
            )
        )
        rows = result.fetchall()
    assert len(rows) == 0, SEQ_GUARD_MSG


def test_no_code_references_purchase_orders_seq():
    """
    Assert no app code or migrations reference purchase_orders_seq.
    Scan /app/app and /app/alembic/versions only (not /app/tests).
    """
    app_root = Path("/app/app")
    for path in app_root.rglob("*.py"):
        content = path.read_text(errors="ignore")
        if "purchase_orders_seq" in content:
            pytest.fail(
                f"{SEQ_GUARD_MSG} Found reference in: {path}"
            )
    for path in Path("/app/alembic/versions").rglob("*.py"):
        content = path.read_text(errors="ignore")
        if "purchase_orders_seq" in content:
            pytest.fail(
                f"{SEQ_GUARD_MSG} Found reference in: {path}"
            )
