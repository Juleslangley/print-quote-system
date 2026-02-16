from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.api.permissions import require_admin
from app.core.db import get_db
from app.models.base import new_id
from app.models.document_template import DocumentTemplate
from app.models.user import User
from app.schemas.document_template import DocumentTemplateCreate, DocumentTemplateOut, DocumentTemplateUpdate

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


@router.post("/document-templates", response_model=DocumentTemplateOut)
def create_template(
    payload: DocumentTemplateCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    _validate_doc_type(payload.doc_type)
    t = DocumentTemplate(
        id=new_id(),
        doc_type=payload.doc_type,
        name=payload.name or "",
        engine=payload.engine or "html_jinja",
        content=payload.content or "",
        is_active=bool(payload.is_active),
    )
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
    if "is_active" in data and data["is_active"] is True:
        db.query(DocumentTemplate).filter(DocumentTemplate.doc_type == t.doc_type, DocumentTemplate.is_active.is_(True)).update(
            {"is_active": False},
            synchronize_session=False,
        )
    for k, v in data.items():
        setattr(t, k, v)
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

