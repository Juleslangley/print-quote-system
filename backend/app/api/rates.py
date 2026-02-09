from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.models.rate import Rate
from app.models.base import new_id
from app.schemas.rate import RateCreate, RateUpdate, RateOut
from app.api.deps import require_admin, get_current_user

router = APIRouter()

@router.get("/rates", response_model=list[RateOut])
def list_rates(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return db.query(Rate).order_by(Rate.rate_type.asc()).all()

@router.get("/rates/{rate_id}", response_model=RateOut)
def get_rate(rate_id: str, db: Session = Depends(get_db), _=Depends(get_current_user)):
    r = db.query(Rate).filter(Rate.id == rate_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Rate not found")
    return r

@router.post("/rates", response_model=RateOut)
def create_rate(payload: RateCreate, db: Session = Depends(get_db), _=Depends(require_admin)):
    r = Rate(id=new_id(), **payload.model_dump())
    db.add(r); db.commit(); db.refresh(r)
    return r

@router.put("/rates/{rate_id}", response_model=RateOut)
def update_rate(rate_id: str, payload: RateUpdate, db: Session = Depends(get_db), _=Depends(require_admin)):
    r = db.query(Rate).filter(Rate.id == rate_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Rate not found")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(r, k, v)
    db.add(r); db.commit(); db.refresh(r)
    return r

@router.delete("/rates/{rate_id}")
def delete_rate(rate_id: str, db: Session = Depends(get_db), _=Depends(require_admin)):
    r = db.query(Rate).filter(Rate.id == rate_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Rate not found")
    db.delete(r); db.commit()
    return {"ok": True}
