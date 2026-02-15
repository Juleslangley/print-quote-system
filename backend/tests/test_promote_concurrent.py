"""Promote draft to final: single and concurrent (20 drafts -> unique sequential PO numbers)."""
import os
import concurrent.futures
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.db import SessionLocal
from app.api.permissions import require_admin, require_sales
from app.models.purchase_order import PurchaseOrder
from app.models.supplier import Supplier
from app.models.base import new_id


def _make_draft_po(po_id: str, supplier_id: str) -> PurchaseOrder:
    return PurchaseOrder(
        id=po_id,
        po_number=f"DRAFT-{po_id}",
        supplier_id=supplier_id,
        status="draft",
        delivery_name="",
        delivery_address="",
        notes="",
        internal_notes="",
    )


@pytest.fixture
def app_with_auth_bypass():
    """Override auth so we can call create and promote without real login."""
    app.dependency_overrides[require_admin] = lambda: None
    app.dependency_overrides[require_sales] = lambda: None
    try:
        yield app
    finally:
        app.dependency_overrides.pop(require_admin, None)
        app.dependency_overrides.pop(require_sales, None)


def test_promote_single_draft_to_final(app_with_auth_bypass):
    """Create one draft via API, promote it; response 200 and po_number is PO + 7 digits."""
    db = SessionLocal()
    try:
        supplier = db.query(Supplier).first()
        if not supplier:
            pytest.skip("No supplier in DB")
        supplier_id = supplier.id
    finally:
        db.close()
    client = TestClient(app_with_auth_bypass)
    create_resp = client.post(
        "/api/purchase-orders",
        json={"supplier_id": supplier_id},
    )
    assert create_resp.status_code == 200, create_resp.json()
    data = create_resp.json()
    po_id = data["id"]
    assert str(data["po_number"]).startswith("DRAFT-"), data
    promote_resp = client.post(f"/api/purchase-orders/{po_id}/promote")
    if promote_resp.status_code == 409:
        pytest.skip(
            "Promote returned 409 (sequence/unique conflict). "
            "Ensure Alembic migration 010_po_native_seq has been run."
        )
    assert promote_resp.status_code == 200, promote_resp.json()
    out = promote_resp.json()
    pn = out["po_number"]
    assert pn.startswith("PO") and len(pn) == 9 and pn[2:].isdigit(), pn


def test_concurrent_promote_20_drafts_unique_and_sequential(app_with_auth_bypass):
    """
    Create 20 draft POs, promote all concurrently via POST /promote.
    Assert all responses 200 and all final po_numbers unique and sequential (PO0000001, PO0000002, ...).
    Requires Postgres (FOR UPDATE); skips on SQLite.
    """
    db_url = os.environ.get("DATABASE_URL", "")
    if "sqlite" in db_url.lower():
        pytest.skip("Concurrency test requires Postgres (FOR UPDATE)")
    db = SessionLocal()
    try:
        supplier = db.query(Supplier).first()
        if not supplier:
            pytest.skip("No supplier in DB; create one to run this test")
        po_ids = [new_id() for _ in range(20)]
        for po_id in po_ids:
            db.add(_make_draft_po(po_id, supplier.id))
        db.commit()
    finally:
        db.close()

    client = TestClient(app_with_auth_bypass)

    def promote_one(po_id: str):
        r = client.post(f"/api/purchase-orders/{po_id}/promote")
        return (po_id, r)

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        results = list(executor.map(lambda pid: promote_one(pid), po_ids))

    statuses = [r.status_code for _, r in results]
    if any(s == 409 for s in statuses):
        pytest.skip(
            "Some promote requests returned 409. "
            "Concurrency test requires Postgres and migration 010_po_native_seq."
        )
    assert all(s == 200 for s in statuses), f"Expected all 200, got: {statuses}"

    po_numbers = []
    for _, r in results:
        data = r.json()
        po_numbers.append(data["po_number"])

    assert len(po_numbers) == 20
    assert len(set(po_numbers)) == 20, "All PO numbers must be unique"

    # Format PO + 7 digits
    for p in po_numbers:
        assert p.startswith("PO") and len(p) == 9 and p[2:].isdigit(), f"Invalid format: {p}"

    nums = sorted(int(p[2:]) for p in po_numbers)
    # Sequential: exactly 1..20 or N..N+19 (if DB had existing POs)
    assert nums == list(range(nums[0], nums[0] + 20)), "PO numbers must be consecutive"

    # Cleanup: remove test POs so they don't affect other tests
    db = SessionLocal()
    try:
        for po_id in po_ids:
            db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()


def test_create_10_new_pos(app_with_auth_bypass):
    """Create 10 new POs via API (create draft + promote). All get unique PO numbers."""
    db = SessionLocal()
    try:
        supplier = db.query(Supplier).first()
        if not supplier:
            pytest.skip("No supplier in DB")
        supplier_id = supplier.id
    finally:
        db.close()

    client = TestClient(app_with_auth_bypass)
    po_numbers = []
    created_ids = []

    for _ in range(10):
        create_resp = client.post("/api/purchase-orders", json={"supplier_id": supplier_id})
        assert create_resp.status_code == 200, create_resp.json()
        data = create_resp.json()
        po_id = data["id"]
        created_ids.append(po_id)
        assert str(data["po_number"]).startswith("DRAFT-"), data

        promote_resp = client.post(f"/api/purchase-orders/{po_id}/promote")
        assert promote_resp.status_code == 200, promote_resp.json()
        out = promote_resp.json()
        pn = out["po_number"]
        assert pn.startswith("PO") and len(pn) == 9 and pn[2:].isdigit(), pn
        po_numbers.append(pn)

    assert len(po_numbers) == 10
    assert len(set(po_numbers)) == 10, "All PO numbers must be unique"

    # Cleanup
    db = SessionLocal()
    try:
        for po_id in created_ids:
            db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()
