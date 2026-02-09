from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.models.machine import Machine
from app.models.machine_rate import MachineRate
from app.models.base import new_id
from app.schemas.machine_rate import MachineRateCreate, MachineRateUpdate, MachineRateOut
from app.api.permissions import require_admin, require_sales

router = APIRouter()


@router.get("/machine-rates", response_model=list[MachineRateOut])
def list_machine_rates(
    machine_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(require_sales),
):
    q = db.query(MachineRate).order_by(MachineRate.machine_id.asc(), MachineRate.sort_order.asc())
    if machine_id:
        q = q.filter(MachineRate.machine_id == machine_id)
    return q.all()


@router.post("/machine-rates", response_model=MachineRateOut)
def create_machine_rate(
    payload: MachineRateCreate, db: Session = Depends(get_db), _=Depends(require_admin)
):
    m = db.query(Machine).filter(Machine.id == payload.machine_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Machine not found")
    r = MachineRate(id=new_id(), **payload.model_dump())
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


@router.put("/machine-rates/{rate_id}", response_model=MachineRateOut)
def update_machine_rate(
    rate_id: str, payload: MachineRateUpdate, db: Session = Depends(get_db), _=Depends(require_admin)
):
    r = db.query(MachineRate).filter(MachineRate.id == rate_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Machine rate not found")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(r, k, v)
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


@router.delete("/machine-rates/{rate_id}")
def delete_machine_rate(rate_id: str, db: Session = Depends(get_db), _=Depends(require_admin)):
    r = db.query(MachineRate).filter(MachineRate.id == rate_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Machine rate not found")
    # Deactivate instead of hard delete so history is preserved
    r.active = False
    db.add(r)
    db.commit()
    return {"ok": True, "deactivated": True}
