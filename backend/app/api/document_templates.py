from __future__ import annotations

import mimetypes
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File as UploadFileParam
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.permissions import require_admin
from app.core.config import settings
from app.core.db import get_db
from app.models.base import new_id
from app.models.document_template import DocumentTemplate
from app.models.file import File as FileRow
from app.models.user import User
from app.schemas.document_template import DocumentTemplateOut, DocumentTemplateTypesOut

router = APIRouter()


DOC_TYPES: list[str] = [
    "purchase_order",
    "invoice",
    "quote",
    "credit_note",
    "production_order",
]

DOC_TYPE_LABELS: dict[str, str] = {
    "purchase_order": "Purchase Order",
    "invoice": "Invoice",
    "quote": "Quote",
    "credit_note": "Credit Note",
    "production_order": "Production Order",
}


def _validate_doc_type(doc_type: str) -> str:
    if doc_type not in DOC_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid doc_type. Must be one of: {', '.join(DOC_TYPES)}")
    return doc_type


# Uploads dir relative to backend root (backend = parent of app)
_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
UPLOADS_DIR = _BACKEND_ROOT / settings.UPLOADS_DIR


def _ensure_uploads():
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    (UPLOADS_DIR / "documents").mkdir(exist_ok=True)


def _guess_mime(filename: str) -> str:
    if not filename:
        return "application/octet-stream"
    mt, _ = mimetypes.guess_type(filename)
    return mt or "application/octet-stream"


def _to_out(db: Session, t: DocumentTemplate) -> DocumentTemplateOut:
    file_storage_key = None
    file_mime = None
    file_size = None
    if t.file_id:
        f = db.query(FileRow).filter(FileRow.id == t.file_id).first()
        if f:
            file_storage_key = f.storage_key
            file_mime = f.mime
            file_size = f.size
    return DocumentTemplateOut(
        id=t.id,
        doc_type=t.doc_type,
        name=t.name,
        active=t.active,
        file_id=t.file_id,
        filename=t.filename or "",
        file_storage_key=file_storage_key,
        file_mime=file_mime,
        file_size=file_size,
        created_at=getattr(t, "created_at", None),
        updated_at=getattr(t, "updated_at", None),
    )


@router.get("/document-templates/types", response_model=DocumentTemplateTypesOut)
def list_document_template_types(_: User = Depends(require_admin)):
    return {"types": DOC_TYPES}


@router.get("/document-templates", response_model=list[DocumentTemplateOut])
def list_document_templates(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    rows = db.query(DocumentTemplate).order_by(DocumentTemplate.doc_type.asc()).all()
    return [_to_out(db, r) for r in rows]


@router.get("/document-templates/{doc_type}", response_model=DocumentTemplateOut)
def get_document_template(doc_type: str, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    _validate_doc_type(doc_type)
    row = db.query(DocumentTemplate).filter(DocumentTemplate.doc_type == doc_type).first()
    if not row:
        # return a placeholder so the admin UI can display "no file uploaded"
        row = DocumentTemplate(
            id="",
            doc_type=doc_type,
            name=DOC_TYPE_LABELS.get(doc_type, doc_type),
            active=True,
            file_id=None,
            filename="",
        )
        return _to_out(db, row)
    return _to_out(db, row)


@router.post("/document-templates/{doc_type}/upload", response_model=DocumentTemplateOut)
def upload_document_template(
    doc_type: str,
    file: UploadFile = UploadFileParam(),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    _validate_doc_type(doc_type)
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No file")
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Upload a .pdf file")
    content = file.file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    _ensure_uploads()

    existing = db.query(DocumentTemplate).filter(DocumentTemplate.doc_type == doc_type).first()
    old_file_id = existing.file_id if existing else None

    file_id = new_id()
    ext = "pdf"
    storage_key = f"documents/{doc_type}/{file_id}.{ext}"
    path = UPLOADS_DIR / storage_key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)

    file_row = FileRow(
        id=file_id,
        storage_key=storage_key,
        mime=_guess_mime(file.filename),
        size=len(content),
        sha256="",
        uploaded_by=user.id,
    )
    db.add(file_row)
    db.flush()

    if not existing:
        existing = DocumentTemplate(
            id=new_id(),
            doc_type=doc_type,
            name=DOC_TYPE_LABELS.get(doc_type, doc_type),
            active=True,
            file_id=file_id,
            filename=file.filename or "",
        )
    else:
        existing.file_id = file_id
        existing.filename = file.filename or ""
        existing.active = True
    db.add(existing)

    # Best-effort cleanup of old file row + bytes
    if old_file_id:
        old = db.query(FileRow).filter(FileRow.id == old_file_id).first()
        if old:
            try:
                (UPLOADS_DIR / old.storage_key).unlink(missing_ok=True)  # type: ignore[arg-type]
            except Exception:
                pass
            db.delete(old)

    db.commit()
    db.refresh(existing)
    return _to_out(db, existing)


@router.get("/document-templates/{doc_type}/download")
def download_document_template(doc_type: str, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    _validate_doc_type(doc_type)
    t = db.query(DocumentTemplate).filter(DocumentTemplate.doc_type == doc_type).first()
    if not t or not t.file_id:
        raise HTTPException(status_code=404, detail="No template uploaded")
    f = db.query(FileRow).filter(FileRow.id == t.file_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="Template file not found")
    path = UPLOADS_DIR / f.storage_key
    if not path.exists():
        raise HTTPException(status_code=404, detail="Template file missing on disk")
    data = path.read_bytes()
    filename = t.filename or f"{doc_type}.pdf"
    return Response(
        content=data,
        media_type=f.mime or "application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/document-templates/{doc_type}/view")
def view_document_template(doc_type: str, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    """Open the template inline in the browser (preview)."""
    _validate_doc_type(doc_type)
    t = db.query(DocumentTemplate).filter(DocumentTemplate.doc_type == doc_type).first()
    if not t or not t.file_id:
        raise HTTPException(status_code=404, detail="No template uploaded")
    f = db.query(FileRow).filter(FileRow.id == t.file_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="Template file not found")
    path = UPLOADS_DIR / f.storage_key
    if not path.exists():
        raise HTTPException(status_code=404, detail="Template file missing on disk")
    data = path.read_bytes()
    filename = t.filename or f"{doc_type}.pdf"
    return Response(
        content=data,
        media_type=f.mime or "application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.delete("/document-templates/{doc_type}")
def delete_document_template(doc_type: str, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    _validate_doc_type(doc_type)
    t = db.query(DocumentTemplate).filter(DocumentTemplate.doc_type == doc_type).first()
    if not t:
        return {"ok": True}
    if t.file_id:
        f = db.query(FileRow).filter(FileRow.id == t.file_id).first()
        if f:
            try:
                (UPLOADS_DIR / f.storage_key).unlink(missing_ok=True)  # type: ignore[arg-type]
            except Exception:
                pass
            db.delete(f)
    t.file_id = None
    t.filename = ""
    db.add(t)
    db.commit()
    return {"ok": True}

