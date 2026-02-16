import pytest

from app.core.db import SessionLocal
from app.models.base import new_id
from app.models.user import User
from app.models.supplier import Supplier
from app.models.purchase_order import PurchaseOrder
from app.models.purchase_order_line import PurchaseOrderLine
from app.models.document_template import DocumentTemplate
from app.models.file import File as FileRow
from app.services.document_renderer import render_purchase_order_for_session


def test_render_purchase_order_smoke_creates_file_and_pdf(tmp_path):
    """
    Smoke test:
    - create supplier + user + PO + line + active template
    - render purchase order
    - assert File row exists and PDF exists on disk

    If WeasyPrint system deps are missing in the test environment, skip.
    """
    try:
        import weasyprint  # noqa: F401
    except Exception as e:
        pytest.skip(f"WeasyPrint not available in test env: {e}")

    db = SessionLocal()
    created_paths = []
    try:
        user = User(id=new_id(), email=f"t-{new_id()}@local", password_hash="x", role="admin", active=True)
        sup = Supplier(id=new_id(), name=f"Test Supplier {new_id()}", active=True)
        po_id = new_id()
        po = PurchaseOrder(id=po_id, po_number=f"DRAFT-{po_id}", supplier_id=sup.id, status="draft")
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
        tpl = DocumentTemplate(
            id=new_id(),
            doc_type="purchase_order",
            name="Smoke PO",
            engine="html_jinja",
            content="<html><body><h1>PO {{ po.id }}</h1></body></html>",
            is_active=True,
        )
        # Ensure only one active
        db.query(DocumentTemplate).filter(DocumentTemplate.doc_type == "purchase_order").update({"is_active": False}, synchronize_session=False)

        db.add_all([user, sup, po, line, tpl])
        db.commit()

        file_id = render_purchase_order_for_session(db, po_id, user.id)
        db.commit()

        f = db.query(FileRow).filter(FileRow.id == file_id).first()
        assert f is not None
        assert f.storage_key.endswith(".pdf")

        # Resolve path relative to backend root (this matches service logic).
        import pathlib
        backend_root = pathlib.Path(__file__).resolve().parent.parent
        pdf_path = backend_root / f.storage_key
        created_paths.append(pdf_path)
        assert pdf_path.exists()
        assert pdf_path.stat().st_size > 0
    except OSError as e:
        # Common when WeasyPrint's native deps are unavailable on CI.
        pytest.skip(f"WeasyPrint native deps missing: {e}")
    finally:
        # Best-effort cleanup
        for p in created_paths:
            try:
                p.unlink(missing_ok=True)  # type: ignore[arg-type]
            except Exception:
                pass
        db.close()

