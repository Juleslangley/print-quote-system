import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError
from app.core.db import get_db
from app.api.permissions import require_admin, require_sales
from app.models.employer import Employer
from app.models.base import new_id
from app.schemas.employer import EmployerCreate, EmployerUpdate, EmployerOut

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/employers", response_model=list[EmployerOut])
def list_employers(db: Session = Depends(get_db), _=Depends(require_sales)):
    try:
        return db.query(Employer).order_by(Employer.name.asc()).all()
    except OperationalError as e:
        logger.warning("GET /api/employers: table may be missing, returning []: %s", e)
        return []


@router.get("/employers/{employer_id}", response_model=EmployerOut)
def get_employer(employer_id: str, db: Session = Depends(get_db), _=Depends(require_sales)):
    e = db.query(Employer).filter(Employer.id == employer_id).first()
    if not e:
        raise HTTPException(status_code=404, detail="Employer not found")
    return e


@router.post("/employers", response_model=EmployerOut)
def create_employer(payload: EmployerCreate, db: Session = Depends(get_db), _=Depends(require_admin)):
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")
    exists = db.query(Employer).filter(Employer.name == name).first()
    if exists:
        raise HTTPException(status_code=400, detail="Employer name already exists")

    data = payload.model_dump()
    data["name"] = name
    e = Employer(id=new_id(), **data)
    db.add(e)
    db.commit()
    db.refresh(e)
    return e


@router.put("/employers/{employer_id}", response_model=EmployerOut)
def update_employer(employer_id: str, payload: EmployerUpdate, db: Session = Depends(get_db), _=Depends(require_admin)):
    e = db.query(Employer).filter(Employer.id == employer_id).first()
    if not e:
        raise HTTPException(status_code=404, detail="Employer not found")

    data = payload.model_dump(exclude_unset=True)
    if "name" in data and data["name"] is not None:
        name = data["name"].strip()
        if not name:
            raise HTTPException(status_code=400, detail="Name is required")
        data["name"] = name
        existing = db.query(Employer).filter(Employer.name == name, Employer.id != employer_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Employer name already exists")

    for k, v in data.items():
        setattr(e, k, v)

    db.add(e)
    db.commit()
    db.refresh(e)
    return e


@router.delete("/employers/{employer_id}")
def delete_employer(employer_id: str, db: Session = Depends(get_db), _=Depends(require_admin)):
    e = db.query(Employer).filter(Employer.id == employer_id).first()
    if not e:
        raise HTTPException(status_code=404, detail="Employer not found")
    db.delete(e)
    db.commit()
    return {"ok": True}
