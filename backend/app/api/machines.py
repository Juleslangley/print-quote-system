from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.models.machine import Machine
from app.models.machine_rate import MachineRate
from app.models.base import new_id
from app.schemas.machine import MachineCreate, MachineUpdate, MachineOut, MachineReorderIn
from app.schemas.machine_rate import MachineRateOut
from app.api.deps import get_current_user
from app.api.permissions import require_admin, require_sales

router = APIRouter()


@router.get("/machines", response_model=list[MachineOut])
def list_machines(
    db: Session = Depends(get_db),
    user=Depends(require_sales),
    include_inactive: bool = Query(False, description="Include inactive machines (admin only)"),
):
    q = db.query(Machine).order_by(Machine.sort_order.asc(), Machine.name.asc())
    if not include_inactive or user.role != "admin":
        q = q.filter(Machine.active == True)
    return q.all()


@router.get("/machines/{machine_id}", response_model=MachineOut)
def get_machine(machine_id: str, db: Session = Depends(get_db), _=Depends(require_sales)):
    m = db.query(Machine).filter(Machine.id == machine_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Machine not found")
    return m


@router.post("/machines", response_model=MachineOut)
def create_machine(payload: MachineCreate, db: Session = Depends(get_db), _=Depends(require_admin)):
    if db.query(Machine).filter(Machine.name == payload.name.strip()).first():
        raise HTTPException(status_code=400, detail="Machine with this name already exists")
    m = Machine(id=new_id(), **payload.model_dump())
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


@router.put("/machines/{machine_id}", response_model=MachineOut)
def update_machine(
    machine_id: str, payload: MachineUpdate, db: Session = Depends(get_db), _=Depends(require_admin)
):
    m = db.query(Machine).filter(Machine.id == machine_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Machine not found")
    data = payload.model_dump(exclude_unset=True)
    if "name" in data and data["name"]:
        other = db.query(Machine).filter(Machine.name == data["name"].strip(), Machine.id != machine_id).first()
        if other:
            raise HTTPException(status_code=400, detail="Another machine with this name already exists")
    for k, v in data.items():
        if k == "meta" and v is not None:
            existing = m.meta or {}
            merged = {**existing, **v}
            setattr(m, k, merged)
        elif k == "config" and v is not None:
            existing = getattr(m, "config", None) or {}
            merged = {**existing, **v}
            setattr(m, k, merged)
        else:
            setattr(m, k, v)
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


@router.delete("/machines/{machine_id}")
def delete_machine(machine_id: str, db: Session = Depends(get_db), _=Depends(require_admin)):
    """Soft-deactivate: set active=false. Never hard-deletes to preserve FK history."""
    m = db.query(Machine).filter(Machine.id == machine_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Machine not found")
    m.active = False
    db.add(m)
    db.commit()
    return {"ok": True, "deactivated": True}


@router.post("/machines/reorder")
def reorder_machines(payload: MachineReorderIn, db: Session = Depends(get_db), _=Depends(require_admin)):
    for i, mid in enumerate(payload.ids):
        m = db.query(Machine).filter(Machine.id == mid).first()
        if m:
            m.sort_order = i
            db.add(m)
    db.commit()
    return {"ok": True}


@router.get("/machines/{machine_id}/rates", response_model=list[MachineRateOut])
def list_machine_rates(machine_id: str, db: Session = Depends(get_db), _=Depends(require_sales)):
    m = db.query(Machine).filter(Machine.id == machine_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Machine not found")
    return (
        db.query(MachineRate)
        .filter(MachineRate.machine_id == machine_id)
        .order_by(MachineRate.sort_order.asc(), MachineRate.operation_key.asc())
        .all()
    )
