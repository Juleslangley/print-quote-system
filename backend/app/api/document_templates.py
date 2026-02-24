from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.api.permissions import require_admin
from app.core.db import get_db
from app.models.base import new_id
from app.models.document_template import DocumentTemplate
from app.models.document_template_version import DocumentTemplateVersion
from app.models.purchase_order import PurchaseOrder
from app.models.user import User
from app.schemas.document_template import (
    DocumentTemplateCreate,
    DocumentTemplateOut,
    DocumentTemplatePreview,
    DocumentTemplateUpdate,
)
from app.services.document_preview import render_preview
from app.services.document_renderer import html_to_pdf_bytes
from app.services.document_sanitizer import sanitize_html, sanitize_css
from app.services.document_expand import validate_template_jinja, expand_jinja_blocks, deduplicate_po_lines_tables

router = APIRouter()


ALLOWED_DOC_TYPES = {
    "purchase_order",
    "quote",
    "invoice",
    "credit_note",
    "production_order",
}


def _validate_doc_type(doc_type: str) -> None:
    if doc_type not in ALLOWED_DOC_TYPES:
        raise HTTPException(status_code=400, detail=f"doc_type must be one of {sorted(ALLOWED_DOC_TYPES)}")


@router.get("/document-templates", response_model=list[DocumentTemplateOut])
def list_templates(
    doc_type: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    q = db.query(DocumentTemplate)
    if doc_type:
        _validate_doc_type(doc_type)
        q = q.filter(DocumentTemplate.doc_type == doc_type)
    return q.order_by(DocumentTemplate.doc_type.asc(), DocumentTemplate.created_at.desc()).all()


def _apply_template_fields(t: DocumentTemplate, payload: dict) -> None:
    """Apply and sanitize template fields. Expand, sanitize, then deduplicate (after TipTap unwrap)."""
    if "template_html" in payload and payload["template_html"] is not None:
        html = expand_jinja_blocks(payload["template_html"])
        html = sanitize_html(html) or ""
        html = deduplicate_po_lines_tables(html)
        t.template_html = html or None
    if "template_json" in payload and payload["template_json"] is not None:
        t.template_json = payload["template_json"]  # JSON is not HTML, store as-is
    if "template_css" in payload and payload["template_css"] is not None:
        t.template_css = sanitize_css(payload["template_css"]) or None
    if "content" in payload and payload["content"] is not None:
        t.content = sanitize_html(payload["content"]) or ""


def _validate_template_content(template_html: str | None, content: str) -> None:
    """Raise HTTPException if template has Jinja syntax errors (e.g. unbalanced blocks)."""
    body = (template_html or "") or (content or "")
    if not body.strip():
        return
    ok, err = validate_template_jinja(template_html or "", content=content or "")
    if not ok:
        raise HTTPException(status_code=400, detail=err)


@router.post("/document-templates", response_model=DocumentTemplateOut)
def create_template(
    payload: DocumentTemplateCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    _validate_doc_type(payload.doc_type)
    _validate_template_content(payload.template_html, payload.content or "")
    data = payload.model_dump()
    t = DocumentTemplate(
        id=new_id(),
        doc_type=payload.doc_type,
        name=payload.name or "",
        engine=payload.engine or "html_jinja",
        content=payload.content or "",
        is_active=bool(payload.is_active),
    )
    _apply_template_fields(t, data)
    if t.is_active:
        db.query(DocumentTemplate).filter(DocumentTemplate.doc_type == t.doc_type, DocumentTemplate.is_active.is_(True)).update(
            {"is_active": False},
            synchronize_session=False,
        )
    db.add(t)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=f"Template activation conflict: {e.orig}")
    db.refresh(t)
    return t


def _get_preview_template_content(
    payload: DocumentTemplatePreview,
    db: Session,
) -> tuple[str | None, str | None]:
    """
    Resolve template_html and template_css for preview.
    When purchase_order + entity_id and no template content provided, use active PO template.
    """
    if payload.template_html or payload.template_css or (payload.content or "").strip():
        return payload.template_html, payload.template_css
    if payload.doc_type == "purchase_order" and payload.entity_id:
        tpl = (
            db.query(DocumentTemplate)
            .filter(DocumentTemplate.doc_type == "purchase_order", DocumentTemplate.is_active.is_(True))
            .order_by(DocumentTemplate.updated_at.desc().nullslast(), DocumentTemplate.created_at.desc().nullslast())
            .first()
        )
        if tpl:
            return tpl.template_html or "", tpl.template_css or ""
    return None, None


@router.post("/document-templates/preview")
def preview_template(
    payload: DocumentTemplatePreview,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
    format: Literal["html", "pdf"] = Query("html"),
):
    """
    Render template for preview. Uses template_html+template_css when provided, else content.
    For purchase_order + entity_id with no template content, uses active PO template.
    format=html (default): return HTML.
    format=pdf: render to HTML, convert to PDF, return as attachment.
    """
    _validate_doc_type(payload.doc_type)
    template_html, template_css = _get_preview_template_content(payload, db)
    if template_html is None and template_css is None:
        template_html = payload.template_html
        template_css = payload.template_css
    html = render_preview(
        template_html,
        template_css,
        payload.content or "",
        payload.doc_type,
        entity_id=payload.entity_id,
        db=db,
    )
    if format == "html":
        return HTMLResponse(html)

    # format == "pdf"
    try:
        pdf_bytes = html_to_pdf_bytes(html)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    filename = f"{payload.doc_type}_preview.pdf"
    if payload.doc_type == "purchase_order" and payload.entity_id:
        try:
            po_id = int(payload.entity_id)
            po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
            if po and po.po_number:
                safe_num = "".join(c for c in str(po.po_number) if c.isalnum() or c in "_-")
                filename = f"PO_{safe_num}.pdf"
        except (ValueError, TypeError):
            pass
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.put("/document-templates/{template_id}", response_model=DocumentTemplateOut)
def update_template(
    template_id: str,
    payload: DocumentTemplateUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    t = db.query(DocumentTemplate).filter(DocumentTemplate.id == template_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")
    data = payload.model_dump(exclude_unset=True)
    if "template_html" in data or "content" in data:
        html = data.get("template_html") if "template_html" in data else (t.template_html or "")
        content = data.get("content") if "content" in data else (t.content or "")
        _validate_template_content(html, content)
    if "is_active" in data and data["is_active"] is True:
        db.query(DocumentTemplate).filter(DocumentTemplate.doc_type == t.doc_type, DocumentTemplate.is_active.is_(True)).update(
            {"is_active": False},
            synchronize_session=False,
        )
    _apply_template_fields(t, data)
    for k in ("name", "content", "is_active"):
        if k in data:
            setattr(t, k, data[k])
    # Versioning: create new version row on save
    version = DocumentTemplateVersion(
        id=new_id(),
        template_id=t.id,
        template_html=t.template_html,
        template_json=t.template_json,
        template_css=t.template_css,
    )
    db.add(version)
    db.add(t)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=f"Template activation conflict: {e.orig}")
    db.refresh(t)
    return t


@router.post("/document-templates/{template_id}/activate", response_model=DocumentTemplateOut)
def activate_template(
    template_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    t = db.query(DocumentTemplate).filter(DocumentTemplate.id == template_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")
    # Single transaction: deactivate all, activate requested, commit once.
    db.query(DocumentTemplate).filter(DocumentTemplate.doc_type == t.doc_type).update(
        {"is_active": False},
        synchronize_session=False,
    )
    t.is_active = True
    db.add(t)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Could not activate template due to a concurrent update. Please refresh and try again.",
        )
    db.refresh(t)
    return t


@router.delete("/document-templates/{template_id}")
def delete_template(
    template_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    t = db.query(DocumentTemplate).filter(DocumentTemplate.id == template_id).first()
    if not t:
        return {"ok": True}
    db.delete(t)
    db.commit()
    return {"ok": True}

