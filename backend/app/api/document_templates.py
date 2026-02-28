import re
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, Response, JSONResponse
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
    DocumentTemplateVersionOut,
)
from app.services.document_preview import render_preview, render_preview_with_debug
from app.services.document_renderer import html_to_pdf_bytes
from app.services.document_sanitizer import sanitize_html, sanitize_css
from app.services.document_expand import validate_template_jinja, expand_jinja_blocks
from app.services.document_repair import ensure_single_placeholder
from app.services.jinja_normalize import normalize_jinja_operators_in_tokens

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


def _require_po_lines_or_table(html: str) -> None:
    """Raise HTTPException if purchase_order template has no po_lines placeholder or po-lines table."""
    if re.search(r'data-jinja-block=["\']po_lines["\']', html, re.I):
        return
    if re.search(r'data-template-block=["\']po-lines["\']', html, re.I):
        return
    if re.search(r'class=["\'][^"\']*\bpo-lines\b', html, re.I):
        return
    # data-jinja-output wrapper with po-lines table inside innerHTML
    if "data-jinja-output" in html and "po-lines" in html:
        return
    raise HTTPException(
        status_code=400,
        detail="Purchase order template must include a PO lines block. Add one from the editor toolbar.",
    )


def _apply_template_fields(t: DocumentTemplate, payload: dict) -> None:
    """Apply and sanitize template fields. For purchase_order: ensure single placeholders, require po_lines or table."""
    if "template_html" in payload and payload["template_html"] is not None:
        html = normalize_jinja_operators_in_tokens(payload["template_html"])
        if t.doc_type == "purchase_order":
            _require_po_lines_or_table(html)
            html, _ = ensure_single_placeholder(html, "po_lines")
            html, _ = ensure_single_placeholder(html, "po_totals")
        # Expand placeholders/legacy blocks before validation
        expanded = normalize_jinja_operators_in_tokens(expand_jinja_blocks(html, doc_type=t.doc_type))
        ok, err = validate_template_jinja(
            template_html=expanded,
            content="",
            doc_type=t.doc_type,
        )
        if not ok:
            raise HTTPException(status_code=400, detail=err)
        html = sanitize_html(expanded) or ""
        html = normalize_jinja_operators_in_tokens(html)
        t.template_html = html or None
    if "template_json" in payload and payload["template_json"] is not None:
        t.template_json = payload["template_json"]  # JSON is not HTML, store as-is
    if "template_css" in payload and payload["template_css"] is not None:
        t.template_css = sanitize_css(payload["template_css"]) or None
    if "content" in payload:
        t.content = "{}" if payload["content"] is None else (sanitize_html(payload["content"]) or "{}")


def _validate_template_content(
    template_html: str | None,
    doc_type: str = "purchase_order",
) -> None:
    """Raise HTTPException if template_html has Jinja syntax errors. content is never used for validation."""
    body = normalize_jinja_operators_in_tokens(template_html or "")
    if not body.strip():
        return
    ok, err = validate_template_jinja(
        template_html=body,
        content="",
        doc_type=doc_type,
    )
    if not ok:
        raise HTTPException(status_code=400, detail=err)


def _next_version_num(db: Session, template_id: str) -> int:
    from sqlalchemy import func
    r = db.query(func.max(DocumentTemplateVersion.version_num)).filter(
        DocumentTemplateVersion.template_id == template_id
    ).scalar()
    return (r or 0) + 1


@router.post("/document-templates", response_model=DocumentTemplateOut)
def create_template(
    payload: DocumentTemplateCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    _validate_doc_type(payload.doc_type)
    _validate_template_content(payload.template_html, doc_type=payload.doc_type)
    data = payload.model_dump()
    t = DocumentTemplate(
        id=new_id(),
        doc_type=payload.doc_type,
        name=payload.name or "",
        engine=payload.engine or "html_jinja",
        content="{}",
        is_active=bool(payload.is_active),
    )
    _apply_template_fields(t, data)
    if t.content is None:
        t.content = "{}"
    if t.is_active:
        db.query(DocumentTemplate).filter(DocumentTemplate.doc_type == t.doc_type, DocumentTemplate.is_active.is_(True)).update(
            {"is_active": False},
            synchronize_session=False,
        )
    db.add(t)
    db.flush()  # Get t.id for version
    version_num = 1
    version = DocumentTemplateVersion(
        id=new_id(),
        template_id=t.id,
        version_num=version_num,
        template_html=t.template_html,
        template_json=t.template_json,
        template_css=t.template_css,
        created_by=user.id if user else None,
    )
    db.add(version)
    db.flush()
    t.current_version_id = version.id
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=f"Template activation conflict: {e.orig}")
    db.refresh(t)
    return t


@router.get("/document-templates/{template_id}/versions", response_model=list[DocumentTemplateVersionOut])
def list_template_versions(
    template_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """List all versions of a template, newest first."""
    t = db.query(DocumentTemplate).filter(DocumentTemplate.id == template_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")
    versions = (
        db.query(DocumentTemplateVersion)
        .filter(DocumentTemplateVersion.template_id == template_id)
        .order_by(DocumentTemplateVersion.version_num.desc())
        .all()
    )
    return versions


@router.get("/document-templates/{template_id}/versions/{version_id}")
def get_template_version_content(
    template_id: str,
    version_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Get template_html and template_css for a specific version (for preview)."""
    v = (
        db.query(DocumentTemplateVersion)
        .filter(
            DocumentTemplateVersion.template_id == template_id,
            DocumentTemplateVersion.id == version_id,
        )
        .first()
    )
    if not v:
        raise HTTPException(status_code=404, detail="Version not found")
    return {
        "id": v.id,
        "template_id": v.template_id,
        "version_num": v.version_num,
        "template_html": v.template_html or "",
        "template_css": v.template_css or "",
        "created_at": v.created_at.isoformat() if v.created_at else None,
    }


def _get_preview_template_content(
    payload: DocumentTemplatePreview,
    db: Session,
) -> tuple[str | None, str | None, DocumentTemplate | None, str | None]:
    """
    Resolve template_html and template_css for preview.
    Returns (template_html, template_css, template_or_none, template_version_id).
    """
    if payload.template_version_id:
        v = (
            db.query(DocumentTemplateVersion)
            .filter(DocumentTemplateVersion.id == payload.template_version_id)
            .first()
        )
        if v:
            return v.template_html or "", v.template_css or "", None, v.id
    if payload.template_html is not None or payload.template_css is not None:
        return payload.template_html or "", payload.template_css or "", None, None
    if payload.doc_type == "purchase_order" and payload.entity_id:
        tpl = (
            db.query(DocumentTemplate)
            .filter(DocumentTemplate.doc_type == "purchase_order", DocumentTemplate.is_active.is_(True))
            .order_by(DocumentTemplate.updated_at.desc().nullslast(), DocumentTemplate.created_at.desc().nullslast())
            .first()
        )
        if tpl:
            return tpl.template_html or "", tpl.template_css or "", tpl, tpl.current_version_id
    return None, None, None, None


def _get_latest_template_version_id(db: Session, template_id: str) -> str | None:
    from app.models.document_template_version import DocumentTemplateVersion
    v = (
        db.query(DocumentTemplateVersion)
        .filter(DocumentTemplateVersion.template_id == template_id)
        .order_by(DocumentTemplateVersion.created_at.desc().nullslast())
        .first()
    )
    return v.id if v else None


@router.post("/document-templates/preview")
def preview_template(
    payload: DocumentTemplatePreview,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
    format: Literal["html", "pdf"] = Query("html"),
    include_debug: bool = Query(False),
):
    """
    Render template for preview. Uses template_html+template_css when provided, else content.
    For purchase_order + entity_id with no template content, uses active PO template.
    format=html (default): return HTML, or JSON with html+debug when include_debug=true.
    format=pdf: render to HTML, convert to PDF, return as attachment.
    """
    _validate_doc_type(payload.doc_type)
    template_html, template_css, tpl_used, template_version_id = _get_preview_template_content(payload, db)
    if template_html is None and template_css is None:
        template_html = payload.template_html
        template_css = payload.template_css
    template_html = normalize_jinja_operators_in_tokens(template_html or "")

    if tpl_used and not template_version_id:
        template_version_id = tpl_used.current_version_id or _get_latest_template_version_id(db, tpl_used.id)

    if include_debug and format == "html":
        html, debug_info = render_preview_with_debug(
            template_html,
            template_css,
            payload.doc_type,
            entity_id=payload.entity_id,
            db=db,
            template_version_id=template_version_id,
        )
        return JSONResponse({"html": html, "debug": debug_info})

    html = render_preview(
        template_html,
        template_css,
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
    user: User = Depends(require_admin),
):
    t = db.query(DocumentTemplate).filter(DocumentTemplate.id == template_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")
    data = payload.model_dump(exclude_unset=True)
    if "template_html" in data:
        html = data.get("template_html") or ""
        _validate_template_content(html, doc_type=t.doc_type)
    if "is_active" in data and data["is_active"] is True:
        db.query(DocumentTemplate).filter(DocumentTemplate.doc_type == t.doc_type, DocumentTemplate.is_active.is_(True)).update(
            {"is_active": False},
            synchronize_session=False,
        )
        db.flush()
        db.refresh(t)  # Reload t so session sees is_active=False; then setattr will mark it dirty
    _apply_template_fields(t, data)
    for k in ("name", "is_active"):
        if k in data:
            setattr(t, k, data[k])
    if t.content is None:
        t.content = "{}"
    # Versioning: create new version row on save (when template_html/json/css changed)
    if "template_html" in data or "template_json" in data or "template_css" in data:
        version_num = _next_version_num(db, t.id)
        version = DocumentTemplateVersion(
            id=new_id(),
            template_id=t.id,
            version_num=version_num,
            template_html=t.template_html,
            template_json=t.template_json,
            template_css=t.template_css,
            created_by=user.id if user else None,
        )
        db.add(version)
        db.flush()
        t.current_version_id = version.id
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

