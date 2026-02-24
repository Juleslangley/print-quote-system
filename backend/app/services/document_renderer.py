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
from app.services.document_context import build_context
from app.services.document_expand import expand_jinja_blocks


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


def html_to_pdf_bytes(html: str) -> bytes:
    """Convert HTML to PDF bytes. Reusable for preview PDF export."""
    return _html_to_pdf_bytes(html)


def generate_po_pdf_bytes(db: Session, po_id: int) -> bytes:
    """
    Generate PO PDF bytes using the active purchase_order template.
    Does not persist to storage. Raises ValueError if PO not found or no active template.
    """
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise ValueError("Purchase order not found")

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

    if tpl.template_html is not None or tpl.template_css is not None:
        body = expand_jinja_blocks(tpl.template_html or "")
        css = f"<style>\n{tpl.template_css or ''}\n</style>" if tpl.template_css else ""
        template_content = f"<!doctype html><html><head><meta charset=\"utf-8\">{css}</head><body>{body}</body></html>"
    else:
        template_content = expand_jinja_blocks(tpl.content or "")

    context = build_context("purchase_order", str(po_id), db)
    if not context:
        raise ValueError("Failed to build PO context")

    html = _render_html(template_content, context)
    return _html_to_pdf_bytes(html)


def render_purchase_order_for_session(db: Session, po_id: int, user_id: str) -> str:
    """
    DB-session variant (used internally and by API hooks).
    Returns the created file_id.
    """
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise ValueError("Purchase order not found")

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

    # Use template_html + template_css when set, else legacy content
    if tpl.template_html is not None or tpl.template_css is not None:
        body = expand_jinja_blocks(tpl.template_html or "")
        css = f"<style>\n{tpl.template_css or ''}\n</style>" if tpl.template_css else ""
        template_content = f"<!doctype html><html><head><meta charset=\"utf-8\">{css}</head><body>{body}</body></html>"
    else:
        template_content = expand_jinja_blocks(tpl.content or "")

    context = build_context("purchase_order", str(po_id), db)
    if not context:
        raise ValueError("Failed to build PO context")

    html = _render_html(template_content, context)
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

