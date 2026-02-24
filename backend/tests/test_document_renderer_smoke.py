import pathlib

import pytest
from fastapi.testclient import TestClient

import app.models  # noqa: F401 - register models for Base.metadata
from app.models.base import new_id
from app.models.supplier import Supplier
from app.models.purchase_order import PurchaseOrder
from app.models.purchase_order_line import PurchaseOrderLine
from app.models.document_template import DocumentTemplate
from app.models.file import File as FileRow
from app.services.document_renderer import render_purchase_order_for_session


def test_render_purchase_order_smoke_creates_file_and_pdf(tmp_path, db_session, test_user):
    """
    Smoke test:
    - create supplier + PO + line + active template in same transaction (user from fixture)
    - render purchase order
    - assert File row exists and PDF exists on disk

    Schema comes from Alembic migrations (no create_all). If WeasyPrint deps missing, skip.
    """
    try:
        import weasyprint  # noqa: F401
    except Exception as e:
        pytest.skip(f"WeasyPrint not available in test env: {e}")

    db = db_session
    created_paths = []
    cleanup_ids = {}  # supplier_id, po_id, tpl_id for cleanup
    try:
        sup = Supplier(id=new_id(), name=f"Test Supplier {new_id()}", active=True)
        db.add(sup)
        db.flush()  # Insert supplier before PO so FK is satisfied
        po = PurchaseOrder(supplier_id=sup.id, status="draft")
        db.add(po)
        db.flush()
        po_id = po.id
        cleanup_ids = {"supplier_id": sup.id, "po_id": po_id}
        line = PurchaseOrderLine(
            id=new_id(),
            po_id=po_id,
            sort_order=0,
            description="Test line",
            supplier_product_code="SKU-1",
            qty=1,
            uom="sheet",
            unit_cost_gbp=10.0,
            line_total_gbp=10.0,
            active=True,
        )
        # Deactivate any existing purchase_order template so we can create our own (unique constraint)
        db.query(DocumentTemplate).filter(
            DocumentTemplate.doc_type == "purchase_order", DocumentTemplate.is_active.is_(True)
        ).update({"is_active": False}, synchronize_session=False)
        tpl = DocumentTemplate(
            id=new_id(),
            doc_type="purchase_order",
            name="Smoke PO",
            engine="html_jinja",
            content="{}",
            template_html="<html><body><h1>PO {{ po.id }}</h1></body></html>",
            is_active=True,
        )
        db.add_all([line, tpl])
        db.flush()
        cleanup_ids["tpl_id"] = tpl.id
        db.commit()

        file_id = render_purchase_order_for_session(db, po_id, test_user.id)
        db.commit()

        f = db.query(FileRow).filter(FileRow.id == file_id).first()
        assert f is not None
        assert f.storage_key.endswith(".pdf")

        # Resolve path relative to backend root (this matches service logic).
        backend_root = pathlib.Path(__file__).resolve().parent.parent
        pdf_path = backend_root / "uploads" / f.storage_key
        created_paths.append(pdf_path)
        assert pdf_path.exists()
        assert pdf_path.stat().st_size > 0
    except OSError as e:
        # Common when WeasyPrint's native deps are unavailable on CI.
        pytest.skip(f"WeasyPrint native deps missing: {e}")
    finally:
        # Best-effort cleanup: remove created files and test rows
        for p in created_paths:
            try:
                p.unlink(missing_ok=True)  # type: ignore[arg-type]
            except Exception:
                pass
        if cleanup_ids:
            try:
                if "po_id" in cleanup_ids:
                    db.query(PurchaseOrderLine).filter(PurchaseOrderLine.po_id == cleanup_ids["po_id"]).delete(synchronize_session=False)
                    db.query(PurchaseOrder).filter(PurchaseOrder.id == cleanup_ids["po_id"]).delete(synchronize_session=False)
                if "tpl_id" in cleanup_ids:
                    db.query(DocumentTemplate).filter(DocumentTemplate.id == cleanup_ids["tpl_id"]).delete(synchronize_session=False)
                if "supplier_id" in cleanup_ids:
                    db.query(Supplier).filter(Supplier.id == cleanup_ids["supplier_id"]).delete(synchronize_session=False)
                db.commit()
            except Exception:
                db.rollback()


def test_get_po_pdf_endpoint_returns_200_and_pdf(db_session, supplier_id, app_with_auth_bypass):
    """
    Smoke test: GET /api/purchase-orders/{id}/pdf returns 200, application/pdf, body > 1000 bytes.
    Mocks generate_po_pdf_bytes to avoid WeasyPrint blocking in CI/Docker.
    """
    from unittest.mock import patch

    fake_pdf = b"%PDF-1.4 fake\n" + b"x" * 2000  # > 1000 bytes

    db = db_session
    po = PurchaseOrder(supplier_id=supplier_id, status="draft")
    db.add(po)
    db.flush()
    line = PurchaseOrderLine(
        id=new_id(),
        po_id=po.id,
        sort_order=0,
        description="Test line",
        supplier_product_code="SKU-1",
        qty=1,
        uom="sheet",
        unit_cost_gbp=10.0,
        line_total_gbp=10.0,
        active=True,
    )
    db.query(DocumentTemplate).filter(
        DocumentTemplate.doc_type == "purchase_order", DocumentTemplate.is_active.is_(True)
    ).update({"is_active": False}, synchronize_session=False)
    tpl = DocumentTemplate(
        id=new_id(),
        doc_type="purchase_order",
        name="PO PDF Test",
        engine="html_jinja",
        template_html="<div class='po-page'><h1>PO {{ po.po_number or po.id }}</h1></div>",
        template_css=".po-page { font-size: 12px; }",
        is_active=True,
    )
    db.add_all([line, tpl])
    db.commit()
    db.refresh(po)
    po_id = po.id

    try:
        with patch(
            "app.services.document_renderer.get_or_create_po_pdf_bytes",
            return_value=fake_pdf,
        ):
            client = TestClient(app_with_auth_bypass)
            res = client.get(f"/api/purchase-orders/{po_id}/pdf")
        assert res.status_code == 200, res.text
        assert res.headers.get("content-type", "").startswith("application/pdf")
        assert len(res.content) > 1000, "PDF body should be > 1000 bytes"
    finally:
        db.query(PurchaseOrderLine).filter(PurchaseOrderLine.po_id == po_id).delete(synchronize_session=False)
        db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).delete(synchronize_session=False)
        db.query(DocumentTemplate).filter(DocumentTemplate.id == tpl.id).delete(synchronize_session=False)
        db.commit()


def test_get_po_pdf_after_promote_returns_200(db_session, supplier_id, app_with_auth_bypass):
    """GET /api/purchase-orders/{id}/pdf returns 200 after promote/processed."""
    from unittest.mock import patch
    from app.core.db import get_db

    fake_pdf = b"%PDF-1.4 fake\n" + b"x" * 2000
    app = app_with_auth_bypass
    def fake_get_db():
        yield db_session

    app.dependency_overrides[get_db] = fake_get_db
    client = TestClient(app)
    db = db_session
    po_id = None
    tpl_id = None

    try:
        db.query(DocumentTemplate).filter(
            DocumentTemplate.doc_type == "purchase_order", DocumentTemplate.is_active.is_(True)
        ).update({"is_active": False}, synchronize_session=False)
        tpl = DocumentTemplate(
            id=new_id(),
            doc_type="purchase_order",
            name="PO Promote Test",
            engine="html_jinja",
            content="{}",
            template_html="<h1>PO {{ po.po_number or po.id }}</h1>",
            is_active=True,
        )
        db.add(tpl)
        db.flush()
        tpl_id = tpl.id

        po = PurchaseOrder(supplier_id=supplier_id, status="draft")
        db.add(po)
        db.flush()
        line = PurchaseOrderLine(
            id=new_id(),
            po_id=po.id,
            sort_order=0,
            description="X",
            supplier_product_code="S",
            qty=1,
            uom="ea",
            unit_cost_gbp=10.0,
            line_total_gbp=10.0,
            active=True,
        )
        db.add(line)
        db.commit()
        db.refresh(po)
        po_id = po.id

        promote_res = client.post(f"/api/purchase-orders/{po_id}/promote")
        assert promote_res.status_code == 200

        with patch(
            "app.services.document_renderer.get_or_create_po_pdf_bytes",
            return_value=fake_pdf,
        ):
            pdf_res = client.get(f"/api/purchase-orders/{po_id}/pdf")
        assert pdf_res.status_code == 200
        assert pdf_res.headers.get("content-type", "").startswith("application/pdf")
        assert len(pdf_res.content) > 1000
    finally:
        from app.core.db import get_db
        app.dependency_overrides.pop(get_db, None)
        if tpl_id:
            from app.models.document_render import DocumentRender
            from app.models.file import File as FileRow
            drs = db.query(DocumentRender).filter(DocumentRender.template_id == tpl_id).all()
            file_ids = [dr.file_id for dr in drs]
            backend_root = pathlib.Path(__file__).resolve().parent.parent
            for fid in file_ids:
                f = db.query(FileRow).filter(FileRow.id == fid).first()
                if f and f.storage_key:
                    try:
                        (backend_root / "uploads" / f.storage_key).unlink(missing_ok=True)
                    except Exception:
                        pass
            db.query(DocumentRender).filter(DocumentRender.template_id == tpl_id).delete(synchronize_session=False)
            for fid in file_ids:
                db.query(FileRow).filter(FileRow.id == fid).delete(synchronize_session=False)
            # CASCADE on template_id deletes renders; with 035 migration we can delete template directly
            db.query(DocumentTemplate).filter(DocumentTemplate.id == tpl_id).delete(synchronize_session=False)
        if po_id:
            db.query(PurchaseOrderLine).filter(PurchaseOrderLine.po_id == po_id).delete(synchronize_session=False)
            db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).delete(synchronize_session=False)
        db.commit()

