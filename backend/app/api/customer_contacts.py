from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import update
from app.core.db import get_db
from app.models.customer import Customer
from app.models.customer_contact import CustomerContact
from app.models.base import new_id
from app.schemas.customer_contact import (
    CustomerContactCreate,
    CustomerContactUpdate,
    CustomerContactOut,
)
from app.api.permissions import require_sales, require_admin

router = APIRouter()


@router.get("/customers/{customer_id}/contacts", response_model=list[CustomerContactOut])
def list_contacts(
    customer_id: str, db: Session = Depends(get_db), _=Depends(require_sales)
):
    return (
        db.query(CustomerContact)
        .filter(CustomerContact.customer_id == customer_id)
        .order_by(
            CustomerContact.is_primary.desc(),
            CustomerContact.sort_order.asc(),
            CustomerContact.name.asc(),
        )
        .all()
    )


@router.post("/customer-contacts", response_model=CustomerContactOut)
def create_contact(
    payload: CustomerContactCreate,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    cust = db.query(Customer).filter(Customer.id == payload.customer_id).first()
    if not cust:
        raise HTTPException(status_code=404, detail="Customer not found")

    c = CustomerContact(id=new_id(), **payload.model_dump())

    # If setting primary, clear others
    if c.is_primary:
        db.execute(
            update(CustomerContact)
            .where(
                CustomerContact.customer_id == c.customer_id,
                CustomerContact.is_primary == True,
            )
            .values(is_primary=False)
        )

    db.add(c)
    db.commit()
    db.refresh(c)
    return c


@router.put("/customer-contacts/{contact_id}", response_model=CustomerContactOut)
def update_contact(
    contact_id: str,
    payload: CustomerContactUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    c = db.query(CustomerContact).filter(CustomerContact.id == contact_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Contact not found")

    data = payload.model_dump(exclude_unset=True)

    # If set primary true, clear others
    if data.get("is_primary") is True:
        db.execute(
            update(CustomerContact)
            .where(
                CustomerContact.customer_id == c.customer_id,
                CustomerContact.is_primary == True,
            )
            .values(is_primary=False)
        )

    for k, v in data.items():
        setattr(c, k, v)

    db.add(c)
    db.commit()
    db.refresh(c)
    return c


@router.delete("/customer-contacts/{contact_id}")
def delete_contact(
    contact_id: str, db: Session = Depends(get_db), _=Depends(require_admin)
):
    c = db.query(CustomerContact).filter(CustomerContact.id == contact_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Contact not found")
    db.delete(c)
    db.commit()
    return {"ok": True}
