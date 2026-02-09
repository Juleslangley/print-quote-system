from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.models.template import ProductTemplate
from app.models.base import new_id
from app.schemas.template import TemplateCreate, TemplateUpdate, TemplateOut
from app.api.deps import require_admin, get_current_user

router = APIRouter()

@router.get("/templates", response_model=list[TemplateOut])
def list_templates(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return db.query(ProductTemplate).order_by(ProductTemplate.name.asc()).all()

@router.get("/templates/{template_id}", response_model=TemplateOut)
def get_template(template_id: str, db: Session = Depends(get_db), _=Depends(get_current_user)):
    t = db.query(ProductTemplate).filter(ProductTemplate.id == template_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")
    return t

@router.post("/templates", response_model=TemplateOut)
def create_template(payload: TemplateCreate, db: Session = Depends(get_db), _=Depends(require_admin)):
    t = ProductTemplate(id=new_id(), **payload.model_dump())
    db.add(t); db.commit(); db.refresh(t)
    return t

@router.put("/templates/{template_id}", response_model=TemplateOut)
def update_template(template_id: str, payload: TemplateUpdate, db: Session = Depends(get_db), _=Depends(require_admin)):
    t = db.query(ProductTemplate).filter(ProductTemplate.id == template_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(t, k, v)
    db.add(t); db.commit(); db.refresh(t)
    return t

@router.delete("/templates/{template_id}")
def delete_template(template_id: str, db: Session = Depends(get_db), _=Depends(require_admin)):
    t = db.query(ProductTemplate).filter(ProductTemplate.id == template_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")
    db.delete(t); db.commit()
    return {"ok": True}
