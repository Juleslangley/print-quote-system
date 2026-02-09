from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.core.db import get_db
from app.api.permissions import require_sales
from app.models.base import new_id
from app.models.template import ProductTemplate
from app.models.template_links import TemplateOperation, TemplateAllowedMaterial
from app.schemas.template_links import (
    TemplateOperationAdd, TemplateOperationUpdate, TemplateOperationOut,
    TemplateOperationReorder, TemplateAllowedMaterialAdd, TemplateAllowedMaterialOut
)
from app.api.deps import require_admin

router = APIRouter()

# ----------------------------
# Template Operations
# ----------------------------

@router.get("/templates/{template_id}/operations", response_model=list[TemplateOperationOut])
def list_template_operations(template_id: str, db: Session = Depends(get_db), _=Depends(require_admin)):
    return (
        db.query(TemplateOperation)
        .filter(TemplateOperation.template_id == template_id)
        .order_by(TemplateOperation.sort_order.asc())
        .all()
    )

@router.post("/templates/{template_id}/operations", response_model=TemplateOperationOut)
def add_template_operation(template_id: str, payload: TemplateOperationAdd, db: Session = Depends(get_db), _=Depends(require_admin)):
    link = TemplateOperation(
        id=new_id(),
        template_id=template_id,
        operation_id=payload.operation_id,
        sort_order=payload.sort_order,
        params_override=payload.params_override,
    )
    db.add(link); db.commit(); db.refresh(link)
    return link

@router.put("/template-operations/{link_id}", response_model=TemplateOperationOut)
def update_template_operation(link_id: str, payload: TemplateOperationUpdate, db: Session = Depends(get_db), _=Depends(require_admin)):
    link = db.query(TemplateOperation).filter(TemplateOperation.id == link_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="Template operation link not found")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(link, k, v)
    db.add(link); db.commit(); db.refresh(link)
    return link

@router.delete("/template-operations/{link_id}")
def delete_template_operation(link_id: str, db: Session = Depends(get_db), _=Depends(require_admin)):
    link = db.query(TemplateOperation).filter(TemplateOperation.id == link_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="Template operation link not found")
    db.delete(link); db.commit()
    return {"ok": True}

@router.post("/templates/{template_id}/operations/reorder")
def reorder_template_operations(template_id: str, payload: TemplateOperationReorder, db: Session = Depends(get_db), _=Depends(require_admin)):
    """
    Payload: {"items":[{"link_id":"...","sort_order":10}, ...]}
    Only updates links that belong to this template_id.
    """
    if not payload.items:
        return {"ok": True, "updated": 0}

    link_ids = [x.link_id for x in payload.items]
    links = (
        db.query(TemplateOperation)
        .filter(TemplateOperation.id.in_(link_ids))
        .all()
    )
    links_by_id = {l.id: l for l in links}

    updated = 0
    for item in payload.items:
        link = links_by_id.get(item.link_id)
        if not link:
            continue
        if link.template_id != template_id:
            continue
        link.sort_order = item.sort_order
        db.add(link)
        updated += 1

    db.commit()
    return {"ok": True, "updated": updated}

# ----------------------------
# Allowed Materials
# ----------------------------

@router.get("/templates/{template_id}/allowed-materials", response_model=list[TemplateAllowedMaterialOut])
def list_allowed_materials(template_id: str, db: Session = Depends(get_db), _=Depends(require_sales)):
    return (
        db.query(TemplateAllowedMaterial)
        .filter(TemplateAllowedMaterial.template_id == template_id)
        .all()
    )

@router.post("/templates/{template_id}/allowed-materials", response_model=TemplateAllowedMaterialOut)
def add_allowed_material(template_id: str, payload: TemplateAllowedMaterialAdd, db: Session = Depends(get_db), _=Depends(require_admin)):
    # prevent duplicates
    exists = (
        db.query(TemplateAllowedMaterial)
        .filter(TemplateAllowedMaterial.template_id == template_id, TemplateAllowedMaterial.material_id == payload.material_id)
        .first()
    )
    if exists:
        return exists

    link = TemplateAllowedMaterial(id=new_id(), template_id=template_id, material_id=payload.material_id)
    db.add(link); db.commit(); db.refresh(link)
    return link

@router.delete("/template-allowed-materials/{link_id}")
def delete_allowed_material(link_id: str, db: Session = Depends(get_db), _=Depends(require_admin)):
    link = db.query(TemplateAllowedMaterial).filter(TemplateAllowedMaterial.id == link_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="Allowed material link not found")
    db.delete(link); db.commit()
    return {"ok": True}
