from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.models.operation import Operation
from app.models.base import new_id
from app.schemas.operation import OperationCreate, OperationUpdate, OperationOut
from app.api.deps import require_admin, get_current_user

router = APIRouter()

@router.get("/operations", response_model=list[OperationOut])
def list_operations(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return db.query(Operation).order_by(Operation.code.asc()).all()

@router.get("/operations/{operation_id}", response_model=OperationOut)
def get_operation(operation_id: str, db: Session = Depends(get_db), _=Depends(get_current_user)):
    o = db.query(Operation).filter(Operation.id == operation_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="Operation not found")
    return o

@router.post("/operations", response_model=OperationOut)
def create_operation(payload: OperationCreate, db: Session = Depends(get_db), _=Depends(require_admin)):
    # enforce unique code
    exists = db.query(Operation).filter(Operation.code == payload.code).first()
    if exists:
        raise HTTPException(status_code=409, detail="Operation code already exists")
    o = Operation(id=new_id(), **payload.model_dump())
    db.add(o); db.commit(); db.refresh(o)
    return o

@router.put("/operations/{operation_id}", response_model=OperationOut)
def update_operation(operation_id: str, payload: OperationUpdate, db: Session = Depends(get_db), _=Depends(require_admin)):
    o = db.query(Operation).filter(Operation.id == operation_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="Operation not found")
    data = payload.model_dump(exclude_unset=True)
    if "code" in data:
        exists = db.query(Operation).filter(Operation.code == data["code"], Operation.id != operation_id).first()
        if exists:
            raise HTTPException(status_code=409, detail="Operation code already exists")
    for k, v in data.items():
        setattr(o, k, v)
    db.add(o); db.commit(); db.refresh(o)
    return o

@router.delete("/operations/{operation_id}")
def delete_operation(operation_id: str, db: Session = Depends(get_db), _=Depends(require_admin)):
    o = db.query(Operation).filter(Operation.id == operation_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="Operation not found")
    db.delete(o); db.commit()
    return {"ok": True}
