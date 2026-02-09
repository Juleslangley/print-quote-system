from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.models.material import Material
from app.models.material_size import MaterialSize
from app.models.base import new_id
from app.schemas.material_size import MaterialSizeCreate, MaterialSizeUpdate, MaterialSizeOut
from app.api.permissions import require_admin, require_sales

router = APIRouter()


@router.post("/material-sizes", response_model=MaterialSizeOut)
def create_material_size(
    payload: MaterialSizeCreate,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    m = db.query(Material).filter(Material.id == payload.material_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Material not found")
    s = MaterialSize(id=new_id(), **payload.model_dump())
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


@router.put("/material-sizes/{size_id}", response_model=MaterialSizeOut)
def update_material_size(
    size_id: str,
    payload: MaterialSizeUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    s = db.query(MaterialSize).filter(MaterialSize.id == size_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Material size not found")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(s, k, v)
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


@router.delete("/material-sizes/{size_id}")
def delete_material_size(
    size_id: str,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    s = db.query(MaterialSize).filter(MaterialSize.id == size_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Material size not found")
    db.delete(s)
    db.commit()
    return {"ok": True}
