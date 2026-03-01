import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, attributes
from app.core.db import get_db
from app.models.material import Material
from app.models.material_size import MaterialSize
from app.models.supplier import Supplier
from app.models.template import ProductTemplate
from app.models.template_links import TemplateAllowedMaterial
from app.models.base import new_id
from app.schemas.material import MaterialCreate, MaterialUpdate, MaterialOut
from app.schemas.material_size import MaterialSizeOut
from app.api.permissions import require_sales, require_prod_or_better, require_admin
from app.services.job_routing import normalize_job_type, ALL_JOB_TYPES

logger = logging.getLogger(__name__)
router = APIRouter()


def _sync_material_supplier(mat: Material, db: Session) -> None:
    """After setting supplier_id on material, sync legacy supplier name from Supplier."""
    if mat.supplier_id:
        sup = db.query(Supplier).filter(Supplier.id == mat.supplier_id).first()
        if sup:
            mat.supplier = sup.name
    else:
        mat.supplier = ""


def _get_allowed_job_types_from_meta(mat: Material) -> list[str]:
    raw = (mat.meta or {}).get("allowed_job_types")
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for jt in raw:
        if isinstance(jt, str):
            normalized = normalize_job_type(jt)
            if normalized in ALL_JOB_TYPES and normalized not in out:
                out.append(normalized)
    return out


def _set_allowed_job_types_in_meta(mat: Material, values: list[str] | None) -> None:
    meta = dict(mat.meta or {})
    normalized_values: list[str] = []
    for jt in values or []:
        if not isinstance(jt, str):
            continue
        normalized = normalize_job_type(jt)
        if normalized in ALL_JOB_TYPES and normalized not in normalized_values:
            normalized_values.append(normalized)
    if normalized_values:
        meta["allowed_job_types"] = normalized_values
    else:
        meta.pop("allowed_job_types", None)
    mat.meta = meta
    attributes.flag_modified(mat, "meta")


def _attach_allowed_job_types_view(mat: Material) -> Material:
    # Existing materials use meta JSON; expose a computed field for API consumers.
    setattr(mat, "allowed_job_types", _get_allowed_job_types_from_meta(mat))
    return mat


@router.get("/materials", response_model=list[MaterialOut])
def list_materials(
    job_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(require_sales),
):
    mats = db.query(Material).order_by(Material.name.asc()).all()
    if job_type:
        target_job_type = normalize_job_type(job_type)
        def _allows_job_type(m: Material) -> bool:
            allowed = _get_allowed_job_types_from_meta(m)
            if not allowed:
                return True  # no restriction = allow all
            return target_job_type in allowed
        mats = [m for m in mats if _allows_job_type(m)]
    return [_attach_allowed_job_types_view(m) for m in mats]

@router.get("/materials/{material_id}/usage")
def material_usage(material_id: str, db: Session = Depends(get_db), _=Depends(require_sales)):
    try:
        # Default material usage
        defaults = (
            db.query(ProductTemplate)
            .filter(ProductTemplate.default_material_id == material_id)
            .order_by(ProductTemplate.name.asc())
            .all()
        )

        # Allowed materials usage
        allowed_links = (
            db.query(TemplateAllowedMaterial)
            .filter(TemplateAllowedMaterial.material_id == material_id)
            .all()
        )
        allowed_template_ids = [x.template_id for x in allowed_links] or []

        allowed_templates = []
        if allowed_template_ids:
            allowed_templates = (
                db.query(ProductTemplate)
                .filter(ProductTemplate.id.in_(allowed_template_ids))
                .order_by(ProductTemplate.name.asc())
                .all()
            )

        return {
            "material_id": material_id,
            "default_in_templates": [{"id": t.id, "name": t.name, "category": getattr(t, "category", "")} for t in defaults],
            "allowed_in_templates": [{"id": t.id, "name": t.name, "category": getattr(t, "category", "")} for t in allowed_templates],
            "counts": {
                "default_in": len(defaults),
                "allowed_in": len(allowed_templates),
                "allowed_links": len(allowed_links),
            },
        }
    except Exception as e:
        logger.warning("GET /api/materials/%s/usage failed: %s", material_id, e, exc_info=True)
        return {
            "material_id": material_id,
            "default_in_templates": [],
            "allowed_in_templates": [],
            "counts": {"default_in": 0, "allowed_in": 0, "allowed_links": 0},
        }

@router.get("/materials/{material_id}", response_model=MaterialOut)
def get_material(material_id: str, db: Session = Depends(get_db), _=Depends(require_sales)):
    m = db.query(Material).filter(Material.id == material_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Material not found")
    return _attach_allowed_job_types_view(m)


@router.get("/materials/{material_id}/sizes", response_model=list[MaterialSizeOut])
def list_material_sizes(material_id: str, db: Session = Depends(get_db), _=Depends(require_sales)):
    m = db.query(Material).filter(Material.id == material_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Material not found")
    return (
        db.query(MaterialSize)
        .filter(MaterialSize.material_id == material_id)
        .order_by(
            MaterialSize.width_mm.asc(),
            MaterialSize.length_m.asc().nulls_last(),
            MaterialSize.height_mm.asc().nulls_last(),
            MaterialSize.sort_order.asc(),
        )
        .all()
    )

@router.post("/materials", response_model=MaterialOut)
def create_material(payload: MaterialCreate, db: Session = Depends(get_db), _=Depends(require_admin)):
    data = payload.model_dump(exclude={"supplier", "allowed_job_types"})
    m = Material(id=new_id(), **data)
    if payload.supplier_id:
        sup = db.query(Supplier).filter(Supplier.id == payload.supplier_id).first()
        if not sup:
            raise HTTPException(status_code=400, detail="Invalid supplier_id")
    _sync_material_supplier(m, db)
    _set_allowed_job_types_in_meta(m, payload.allowed_job_types)
    db.add(m)
    db.commit()
    db.refresh(m)
    return _attach_allowed_job_types_view(m)

@router.put("/materials/{material_id}", response_model=MaterialOut)
def update_material(material_id: str, payload: MaterialUpdate, db: Session = Depends(get_db), _=Depends(require_admin)):
    m = db.query(Material).filter(Material.id == material_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Material not found")
    data = payload.model_dump(exclude_unset=True)
    if "supplier_id" in data and data["supplier_id"] is not None:
        sup = db.query(Supplier).filter(Supplier.id == data["supplier_id"]).first()
        if not sup:
            raise HTTPException(status_code=400, detail="Invalid supplier_id")
    allowed_job_types_update = data.pop("allowed_job_types", None)
    for k, v in data.items():
        if k == "supplier":
            continue
        setattr(m, k, v)
        if k == "meta" and v is not None:
            attributes.flag_modified(m, "meta")
    if allowed_job_types_update is not None:
        _set_allowed_job_types_in_meta(m, allowed_job_types_update)
    if "supplier_id" in data:
        _sync_material_supplier(m, db)
    db.add(m)
    db.commit()
    db.refresh(m)
    return _attach_allowed_job_types_view(m)

@router.delete("/materials/{material_id}")
def delete_material(material_id: str, db: Session = Depends(get_db), _=Depends(require_admin)):
    m = db.query(Material).filter(Material.id == material_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Material not found")
    db.delete(m); db.commit()
    return {"ok": True}
