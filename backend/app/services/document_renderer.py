from __future__ import annotations

import hashlib
from pathlib import Path

from jinja2 import Environment, BaseLoader, select_autoescape
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import SessionLocal
from app.models.base import new_id
from app.models.document_render import DocumentRender
from app.models.document_template import DocumentTemplate
from app.models.file import File as FileRow
from app.models.purchase_order import PurchaseOrder
from app.models.purchase_order_line import PurchaseOrderLine
from app.models.supplier import Supplier


# Uploads dir relative to backend root (backend = parent of app)
_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
UPLOADS_DIR = _BACKEND_ROOT / settings.UPLOADS_DIR


def _ensure_uploads_dir() -> None:
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    (UPLOADS_DIR / "documents").mkdir(exist_ok=True)


def _jinja_env() -> Environment:
    return Environment(
        loader=BaseLoader(),
        autoescape=select_autoescape(enabled_extensions=("html", "xml")),
    )


def _render_html(template_content: str, context: dict) -> str:
    env = _jinja_env()
    tpl = env.from_string(template_content or "")
    return tpl.render(**context)


def _html_to_pdf_bytes(html: str) -> bytes:
    try:
        from weasyprint import HTML
    except Exception as e:
        raise RuntimeError(f"WeasyPrint not available: {e}")
    return HTML(string=html).write_pdf()


def render_purchase_order_for_session(db: Session, po_id: int, user_id: str) -> str:
    """
    DB-session variant (used internally and by API hooks).
    Returns the created file_id.
    """
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise ValueError("Purchase order not found")
    supplier = db.query(Supplier).filter(Supplier.id == po.supplier_id).first()
    lines = (
        db.query(PurchaseOrderLine)
        .filter(PurchaseOrderLine.po_id == po_id, PurchaseOrderLine.active.is_(True))
        .order_by(PurchaseOrderLine.sort_order.asc(), PurchaseOrderLine.id.asc())
        .all()
    )

    tpl = (
        db.query(DocumentTemplate)
        .filter(DocumentTemplate.doc_type == "purchase_order", DocumentTemplate.is_active.is_(True))
        .order_by(DocumentTemplate.updated_at.desc().nullslast(), DocumentTemplate.created_at.desc().nullslast())
        .first()
    )
    if not tpl:
        raise ValueError("No active purchase_order document template")
    if (tpl.engine or "html_jinja") != "html_jinja":
        raise ValueError("Unsupported template engine")

    context = {
        "company": {
            "name": "Chartwell Press",
        },
        "po": po,
        "supplier": supplier,
        "lines": lines,
        "vat_rate": 0.20,
    }

    html = _render_html(tpl.content, context)
    pdf_bytes = _html_to_pdf_bytes(html)

    _ensure_uploads_dir()
    render_id = new_id()
    file_id = new_id()
    storage_key = f"documents/purchase_order/{po_id}/{render_id}.pdf"
    path = UPLOADS_DIR / storage_key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(pdf_bytes)

    sha256 = hashlib.sha256(pdf_bytes).hexdigest()
    file_row = FileRow(
        id=file_id,
        storage_key=storage_key,
        mime="application/pdf",
        size=len(pdf_bytes),
        sha256=sha256,
        uploaded_by=user_id if user_id else None,
    )
    db.add(file_row)
    db.flush()

    dr = DocumentRender(
        id=render_id,
        doc_type="purchase_order",
        entity_id=po_id,
        template_id=tpl.id,
        file_id=file_id,
        created_by_user_id=user_id if user_id else None,
    )
    db.add(dr)
    return file_id


def render_purchase_order(po_id: int, user_id: str) -> str:
    """
    Render a Purchase Order PDF using the active HTML template.
    Returns the created file_id.
    """
    db = SessionLocal()
    try:
        file_id = render_purchase_order_for_session(db, po_id, user_id)
        db.commit()
        return file_id
    finally:
        db.close()

