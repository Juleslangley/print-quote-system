import pathlib

import pytest

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
            content="<html><body><h1>PO {{ po.id }}</h1></body></html>",
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

