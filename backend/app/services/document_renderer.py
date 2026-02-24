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
from app.models.document_template_version import DocumentTemplateVersion
from app.models.file import File as FileRow
from app.models.purchase_order import PurchaseOrder
from app.services.document_context import build_context, context_version_string, compute_render_hash
from app.services.document_expand import expand_jinja_blocks


# Uploads dir relative to backend root (backend = parent of app)
_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
UPLOADS_DIR = _BACKEND_ROOT / settings.UPLOADS_DIR


def _template_version_id(db: Session, tpl: DocumentTemplate) -> str | None:
    """Use current_version_id if set, else latest by created_at."""
    if tpl.current_version_id:
        return tpl.current_version_id
    v = (
        db.query(DocumentTemplateVersion)
        .filter(DocumentTemplateVersion.template_id == tpl.id)
        .order_by(DocumentTemplateVersion.version_num.desc().nullslast())
        .first()
    )
    return v.id if v else None


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


def get_or_create_po_pdf_bytes(db: Session, po_id: int, user_id: str | None) -> bytes:
    """
    Get PO PDF bytes: return from cache if exists, else generate and persist.
    Never 404 if PO exists; generates on first request.
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

    version_id = _template_version_id(db, tpl)
    context = build_context("purchase_order", str(po_id), db)
    if context and version_id:
        ctx_ver = context_version_string("purchase_order", context)
        r_hash = compute_render_hash(version_id, str(po_id), "purchase_order", ctx_ver)
        cached = (
            db.query(DocumentRender)
            .filter(
                DocumentRender.doc_type == "purchase_order",
                DocumentRender.entity_id == str(po_id),
                DocumentRender.template_version_id == version_id,
                DocumentRender.render_hash == r_hash,
            )
            .first()
        )
        if cached:
            fr = db.query(FileRow).filter(FileRow.id == cached.file_id).first()
            if fr and fr.storage_key:
                path = UPLOADS_DIR / fr.storage_key
                if path.exists():
                    return path.read_bytes()

    # Cache miss: render and persist
    file_id = render_purchase_order_for_session(db, po_id, user_id or "")
    db.commit()
    fr = db.query(FileRow).filter(FileRow.id == file_id).first()
    if fr and fr.storage_key:
        path = UPLOADS_DIR / fr.storage_key
        if path.exists():
            return path.read_bytes()
    raise RuntimeError("Failed to persist or read rendered PDF")


def generate_po_pdf_bytes(db: Session, po_id: int) -> bytes:
    """
    Generate PO PDF bytes using the active purchase_order template.
    Returns cached PDF when possible. Raises ValueError if PO not found or no active template.
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

    version_id = _template_version_id(db, tpl)
    if version_id:
        context = build_context("purchase_order", str(po_id), db)
        if context:
            ctx_ver = context_version_string("purchase_order", context)
            r_hash = compute_render_hash(version_id, str(po_id), "purchase_order", ctx_ver)
            cached = (
                db.query(DocumentRender)
                .filter(
                    DocumentRender.doc_type == "purchase_order",
                    DocumentRender.entity_id == str(po_id),
                    DocumentRender.template_version_id == version_id,
                    DocumentRender.render_hash == r_hash,
                )
                .first()
            )
            if cached:
                fr = db.query(FileRow).filter(FileRow.id == cached.file_id).first()
                if fr and fr.storage_key:
                    path = UPLOADS_DIR / fr.storage_key
                    if path.exists():
                        return path.read_bytes()

    body = expand_jinja_blocks(tpl.template_html or "", doc_type="purchase_order")
    css = tpl.template_css or ""
    css_block = f"<style>\n{css}\n</style>" if css else ""
    template_content = f"<!doctype html><html><head><meta charset=\"utf-8\">{css_block}</head><body>{body}</body></html>"

    context = build_context("purchase_order", str(po_id), db)
    if not context:
        raise ValueError("Failed to build PO context")

    html = _render_html(template_content, context)
    return _html_to_pdf_bytes(html)


def render_purchase_order_for_session(db: Session, po_id: int, user_id: str) -> str:
    """
    DB-session variant (used internally and by API hooks).
    Returns the created file_id. Uses render cache when template version + context unchanged.
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

    version_id = _template_version_id(db, tpl)
    context = build_context("purchase_order", str(po_id), db)
    if not context:
        raise ValueError("Failed to build PO context")

    if version_id:
        ctx_ver = context_version_string("purchase_order", context)
        r_hash = compute_render_hash(version_id, str(po_id), "purchase_order", ctx_ver)
        cached = (
            db.query(DocumentRender)
            .filter(
                DocumentRender.doc_type == "purchase_order",
                DocumentRender.entity_id == str(po_id),
                DocumentRender.template_version_id == version_id,
                DocumentRender.render_hash == r_hash,
            )
            .first()
        )
        if cached:
            return cached.file_id

    # Cache miss: render and persist
    body = expand_jinja_blocks(tpl.template_html or "", doc_type="purchase_order")
    css = tpl.template_css or ""
    css_block = f"<style>\n{css}\n</style>" if css else ""
    template_content = f"<!doctype html><html><head><meta charset=\"utf-8\">{css_block}</head><body>{body}</body></html>"

    html = _render_html(template_content, context)
    pdf_bytes = _html_to_pdf_bytes(html)

    _ensure_uploads_dir()
    render_id = new_id()
    file_id = new_id()
    storage_key = f"documents/purchase_order/{po_id}/{render_id}.pdf"
    path = UPLOADS_DIR / storage_key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(pdf_bytes)

    sha256_hash = hashlib.sha256(pdf_bytes).hexdigest()
    file_row = FileRow(
        id=file_id,
        storage_key=storage_key,
        mime="application/pdf",
        size=len(pdf_bytes),
        sha256=sha256_hash,
        uploaded_by=user_id if user_id else None,
    )
    db.add(file_row)
    db.flush()

    ctx_ver = context_version_string("purchase_order", context)
    r_hash = compute_render_hash(version_id or "", str(po_id), "purchase_order", ctx_ver) if version_id else None

    dr = DocumentRender(
        id=render_id,
        doc_type="purchase_order",
        entity_id=str(po_id),
        template_id=tpl.id,
        template_version_id=version_id,
        render_hash=r_hash,
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

