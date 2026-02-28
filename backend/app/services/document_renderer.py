from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from jinja2 import Environment, BaseLoader, select_autoescape
from sqlalchemy.orm import Session, selectinload, joinedload

from app.core.config import settings
from app.core.db import SessionLocal
from app.models.base import new_id
from app.models.document_render import DocumentRender
from app.models.document_template import DocumentTemplate
from app.models.file import File as FileRow
from app.models.purchase_order import PurchaseOrder
from app.services.document_context import build_context, context_version_string, compute_render_hash
from app.services.po_premium_template import (
    load_purchase_order_premium_template,
    purchase_order_premium_version_id,
)


# Uploads dir relative to backend root (backend = parent of app)
_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
UPLOADS_DIR = _BACKEND_ROOT / settings.UPLOADS_DIR
logger = logging.getLogger(__name__)


def _ensure_uploads_dir() -> None:
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    (UPLOADS_DIR / "documents").mkdir(exist_ok=True)


def _jinja_env() -> Environment:
    return Environment(
        loader=BaseLoader(),
        autoescape=select_autoescape(enabled_extensions=("html", "xml")),
    )


def _active_po_template_meta(db: Session) -> DocumentTemplate:
    """
    Resolve a template row only for metadata foreign-keys/caching.
    We never read template_html/template_css from DB for PO rendering.
    """
    tpl = (
        db.query(DocumentTemplate)
        .filter(DocumentTemplate.doc_type == "purchase_order", DocumentTemplate.is_active.is_(True))
        .order_by(DocumentTemplate.updated_at.desc().nullslast(), DocumentTemplate.created_at.desc().nullslast())
        .first()
    )
    if tpl:
        return tpl
    any_tpl = (
        db.query(DocumentTemplate)
        .filter(DocumentTemplate.doc_type == "purchase_order")
        .order_by(DocumentTemplate.updated_at.desc().nullslast(), DocumentTemplate.created_at.desc().nullslast())
        .first()
    )
    if any_tpl:
        return any_tpl
    raise ValueError("No purchase_order template metadata row found")


def _render_html(template_content: str, context: dict) -> str:
    env = _jinja_env()
    tpl = env.from_string(template_content or "")
    return tpl.render(**context)


def _compute_totals(lines):
    subtotal = 0.0
    for line in lines:
        if isinstance(line, dict):
            subtotal += float(line.get("line_total_gbp", 0) or 0)
        else:
            subtotal += float(getattr(line, "line_total_gbp", 0) or 0)
    vat = subtotal * 0.2
    total = subtotal + vat
    return subtotal, vat, total


def _build_premium_po_context(db: Session, po_id: int) -> dict:
    po = (
        db.query(PurchaseOrder)
        .options(selectinload(PurchaseOrder.lines), joinedload(PurchaseOrder.supplier))
        .filter(PurchaseOrder.id == po_id)
        .first()
    )
    if not po:
        raise ValueError("Purchase order not found")
    lines = [line for line in (po.lines or []) if getattr(line, "active", False)]
    supplier = po.supplier

    subtotal_val = getattr(po, "subtotal_gbp", None)
    vat_val = getattr(po, "vat_gbp", None)
    total_val = getattr(po, "total_gbp", None)
    if not subtotal_val or not vat_val or not total_val:
        subtotal, vat, total = _compute_totals(lines)
        po.subtotal_gbp = subtotal
        po.vat_gbp = vat
        po.total_gbp = total

    logger.info(
        "PO premium render: po_id=%s supplier_id=%s lines=%s",
        po.id,
        po.supplier_id,
        len(lines),
    )

    context = build_context("purchase_order", str(po_id), db) or {}
    context["po"] = po
    context["lines"] = lines
    context["supplier"] = supplier
    context["delivery"] = {
        "name": getattr(po, "delivery_name", "") or "",
        "address": getattr(po, "delivery_address", "") or "",
    }
    return context


def debug_premium_po_context(db: Session, po_id: int) -> dict[str, object]:
    """
    Dev helper: inspect premium PO context data coverage without rendering.
    Returns key diagnostics for supplier/lines presence.
    """
    ctx = _build_premium_po_context(db, po_id)
    supplier = ctx.get("supplier")
    lines = ctx.get("lines") or []
    first_line = lines[0] if lines else None
    return {
        "po_id": po_id,
        "supplier_name": (
            supplier.get("name")
            if isinstance(supplier, dict)
            else getattr(supplier, "name", None)
        ),
        "line_count": len(lines),
        "first_line_description": (
            first_line.get("description")
            if isinstance(first_line, dict)
            else getattr(first_line, "description", None)
        ),
    }


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
    context = _build_premium_po_context(db, po_id)
    po = context["po"]
    tpl = _active_po_template_meta(db)
    version_id = purchase_order_premium_version_id()
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
    context = _build_premium_po_context(db, po_id)
    po = context["po"]
    tpl = _active_po_template_meta(db)
    version_id = purchase_order_premium_version_id()
    if version_id:
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

    po_html, po_css = load_purchase_order_premium_template()
    body = po_html or ""
    css = po_css or ""
    css_block = f"<style>\n{css}\n</style>" if css else ""
    template_content = f"<!doctype html><html><head><meta charset=\"utf-8\">{css_block}</head><body>{body}</body></html>"

    html = _render_html(template_content, context)
    return _html_to_pdf_bytes(html)


def render_purchase_order_for_session(db: Session, po_id: int, user_id: str) -> str:
    """
    DB-session variant (used internally and by API hooks).
    Returns the created file_id. Uses render cache when template version + context unchanged.
    """
    context = _build_premium_po_context(db, po_id)
    po = context["po"]
    tpl = _active_po_template_meta(db)
    version_id = purchase_order_premium_version_id()

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
    po_html, po_css = load_purchase_order_premium_template()
    body = po_html or ""
    css = po_css or ""
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

