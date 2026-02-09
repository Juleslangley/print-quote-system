import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError
from app.core.db import get_db
from app.api.permissions import require_admin, require_sales
from app.models.supplier import Supplier
from app.models.material import Material
from app.models.template import ProductTemplate
from app.models.template_links import TemplateAllowedMaterial
from app.models.base import new_id
from app.schemas.supplier import SupplierCreate, SupplierUpdate, SupplierOut

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/suppliers", response_model=list[SupplierOut])
def list_suppliers(db: Session = Depends(get_db), _=Depends(require_sales)):
    try:
        return db.query(Supplier).order_by(Supplier.name.asc()).all()
    except OperationalError as e:
        logger.warning("GET /api/suppliers: table may be missing, returning []: %s", e)
        return []

@router.get("/suppliers/{supplier_id}/usage")
def supplier_usage(supplier_id: str, db: Session = Depends(get_db), _=Depends(require_sales)):
    try:
        mats = db.query(Material).filter(Material.supplier_id == supplier_id).all()
        mat_ids = [m.id for m in mats] or []

        default_templates = []
        allowed_templates = []

        if mat_ids:
            default_templates = (
                db.query(ProductTemplate)
                .filter(ProductTemplate.default_material_id.in_(mat_ids))
                .all()
            )

            allowed_links = (
                db.query(TemplateAllowedMaterial)
                .filter(TemplateAllowedMaterial.material_id.in_(mat_ids))
                .all()
            )
            allowed_template_ids = list({x.template_id for x in allowed_links})
            if allowed_template_ids:
                allowed_templates = db.query(ProductTemplate).filter(ProductTemplate.id.in_(allowed_template_ids)).all()

        return {
            "supplier_id": supplier_id,
            "materials_count": len(mats),
            "templates_default_count": len(default_templates),
            "templates_allowed_count": len(allowed_templates),
        }
    except Exception as e:
        logger.warning("GET /api/suppliers/%s/usage failed: %s", supplier_id, e, exc_info=True)
        return {
            "supplier_id": supplier_id,
            "materials_count": 0,
            "templates_default_count": 0,
            "templates_allowed_count": 0,
        }

@router.get("/suppliers/{supplier_id}/materials")
def supplier_materials(supplier_id: str, db: Session = Depends(get_db), _=Depends(require_sales)):
    mats = (
        db.query(Material)
        .filter(Material.supplier_id == supplier_id)
        .order_by(Material.name.asc())
        .all()
    )
    return [
        {
            "id": m.id,
            "name": m.name,
            "type": m.type,
            "active": m.active,
            "supplier": m.supplier,
            "supplier_id": m.supplier_id,
            "cost_per_sheet_gbp": m.cost_per_sheet_gbp,
            "sheet_width_mm": m.sheet_width_mm,
            "sheet_height_mm": m.sheet_height_mm,
            "cost_per_lm_gbp": m.cost_per_lm_gbp,
            "roll_width_mm": m.roll_width_mm,
            "min_billable_lm": m.min_billable_lm,
            "waste_pct_default": m.waste_pct_default,
            "meta": getattr(m, "meta", {}) or {},
        }
        for m in mats
    ]

@router.get("/suppliers/{supplier_id}", response_model=SupplierOut)
def get_supplier(supplier_id: str, db: Session = Depends(get_db), _=Depends(require_sales)):
    s = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return s

@router.post("/suppliers", response_model=SupplierOut)
def create_supplier(payload: SupplierCreate, db: Session = Depends(get_db), _=Depends(require_admin)):
    exists = db.query(Supplier).filter(Supplier.name == payload.name).first()
    if exists:
        raise HTTPException(status_code=400, detail="Supplier name already exists")

    s = Supplier(id=new_id(), **payload.model_dump())
    db.add(s)
    db.commit()
    db.refresh(s)
    return s

@router.put("/suppliers/{supplier_id}", response_model=SupplierOut)
def update_supplier(supplier_id: str, payload: SupplierUpdate, db: Session = Depends(get_db), _=Depends(require_admin)):
    s = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Supplier not found")

    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(s, k, v)

    db.add(s)
    db.commit()
    db.refresh(s)
    return s

@router.delete("/suppliers/{supplier_id}")
def delete_supplier(supplier_id: str, db: Session = Depends(get_db), _=Depends(require_admin)):
    s = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Supplier not found")

    in_use = db.query(Material).filter(Material.supplier_id == supplier_id).count()
    if in_use > 0:
        raise HTTPException(status_code=400, detail=f"Supplier is in use by {in_use} material(s). Reassign or remove materials first.")

    db.delete(s)
    db.commit()
    return {"ok": True}
