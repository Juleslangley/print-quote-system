import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, attributes
from app.core.db import get_db
from app.models.customer import Customer
from app.models.base import new_id
from app.schemas.customer import CustomerCreate, CustomerUpdate, CustomerOut
from app.api.permissions import require_sales, require_admin

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/customers", response_model=list[CustomerOut])
def list_customers(db: Session = Depends(get_db), _=Depends(require_sales)):
    return db.query(Customer).order_by(Customer.name.asc()).all()

@router.post("/customers", response_model=CustomerOut)
def create_customer(payload: CustomerCreate, db: Session = Depends(get_db), _=Depends(require_admin)):
    exists = db.query(Customer).filter(Customer.name == payload.name).first()
    if exists:
        raise HTTPException(status_code=400, detail="Customer name already exists")
    try:
        data = payload.model_dump()
        if data.get("meta") is None:
            data["meta"] = {}
        c = Customer(id=new_id(), **data)
        db.add(c)
        db.commit()
        db.refresh(c)
        return c
    except Exception as e:
        logger.exception("POST /api/customers failed")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/customers/{customer_id}", response_model=CustomerOut)
def update_customer(customer_id: str, payload: CustomerUpdate, db: Session = Depends(get_db), _=Depends(require_admin)):
    c = db.query(Customer).filter(Customer.id == customer_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Customer not found")

    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(c, k, v)
        if k == "meta" and v is not None:
            attributes.flag_modified(c, "meta")

    db.add(c); db.commit(); db.refresh(c)
    return c

@router.delete("/customers/{customer_id}")
def delete_customer(customer_id: str, db: Session = Depends(get_db), _=Depends(require_admin)):
    c = db.query(Customer).filter(Customer.id == customer_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Customer not found")
    db.delete(c); db.commit()
    return {"ok": True}

# Optional usage endpoint (wire to quotes later)
@router.get("/customers/{customer_id}/usage")
def customer_usage(customer_id: str, db: Session = Depends(get_db), _=Depends(require_sales)):
    # TODO: when Quote model exists, return quote counts etc.
    return {"customer_id": customer_id, "quotes_count": 0}
