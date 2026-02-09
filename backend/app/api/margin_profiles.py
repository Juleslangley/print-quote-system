from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.models.margin_profile import MarginProfile
from app.models.base import new_id
from app.schemas.margin_profile import MarginProfileCreate, MarginProfileUpdate, MarginProfileOut
from app.api.deps import require_admin, get_current_user

router = APIRouter()

@router.get("/margin-profiles", response_model=list[MarginProfileOut])
def list_profiles(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return db.query(MarginProfile).order_by(MarginProfile.name.asc()).all()

@router.get("/margin-profiles/{profile_id}", response_model=MarginProfileOut)
def get_profile(profile_id: str, db: Session = Depends(get_db), _=Depends(get_current_user)):
    p = db.query(MarginProfile).filter(MarginProfile.id == profile_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Margin profile not found")
    return p

@router.post("/margin-profiles", response_model=MarginProfileOut)
def create_profile(payload: MarginProfileCreate, db: Session = Depends(get_db), _=Depends(require_admin)):
    exists = db.query(MarginProfile).filter(MarginProfile.name == payload.name).first()
    if exists:
        raise HTTPException(status_code=409, detail="Margin profile name already exists")
    p = MarginProfile(id=new_id(), **payload.model_dump())
    db.add(p); db.commit(); db.refresh(p)
    return p

@router.put("/margin-profiles/{profile_id}", response_model=MarginProfileOut)
def update_profile(profile_id: str, payload: MarginProfileUpdate, db: Session = Depends(get_db), _=Depends(require_admin)):
    p = db.query(MarginProfile).filter(MarginProfile.id == profile_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Margin profile not found")
    data = payload.model_dump(exclude_unset=True)
    if "name" in data:
        exists = db.query(MarginProfile).filter(MarginProfile.name == data["name"], MarginProfile.id != profile_id).first()
        if exists:
            raise HTTPException(status_code=409, detail="Margin profile name already exists")
    for k, v in data.items():
        setattr(p, k, v)
    db.add(p); db.commit(); db.refresh(p)
    return p

@router.delete("/margin-profiles/{profile_id}")
def delete_profile(profile_id: str, db: Session = Depends(get_db), _=Depends(require_admin)):
    p = db.query(MarginProfile).filter(MarginProfile.id == profile_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Margin profile not found")
    db.delete(p); db.commit()
    return {"ok": True}
