from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import update
from app.core.db import get_db
from app.models.customer_contact import CustomerContact
from app.models.customer_contact_method import CustomerContactMethod
from app.models.base import new_id
from app.schemas.customer_contact_method import (
    CustomerContactMethodCreate,
    CustomerContactMethodUpdate,
    CustomerContactMethodOut,
)
from app.api.permissions import require_sales, require_admin

VALID_KINDS = frozenset({"phone", "email", "whatsapp", "other"})
router = APIRouter()


def _clear_primary_same_kind(db: Session, contact_id: str, kind: str) -> None:
    db.execute(
        update(CustomerContactMethod)
        .where(
            CustomerContactMethod.contact_id == contact_id,
            CustomerContactMethod.kind == kind,
            CustomerContactMethod.is_primary == True,
        )
        .values(is_primary=False)
    )


@router.get(
    "/customer-contacts/{contact_id}/methods",
    response_model=list[CustomerContactMethodOut],
)
def list_methods(
    contact_id: str,
    db: Session = Depends(get_db),
    _=Depends(require_sales),
):
    contact = db.query(CustomerContact).filter(CustomerContact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return (
        db.query(CustomerContactMethod)
        .filter(CustomerContactMethod.contact_id == contact_id)
        .order_by(
            CustomerContactMethod.kind.asc(),
            CustomerContactMethod.is_primary.desc(),
            CustomerContactMethod.sort_order.asc(),
            CustomerContactMethod.label.asc(),
        )
        .all()
    )


@router.post(
    "/customer-contact-methods",
    response_model=CustomerContactMethodOut,
)
def create_method(
    payload: CustomerContactMethodCreate,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    kind = (payload.kind or "").strip().lower() or "other"
    if kind not in VALID_KINDS:
        raise HTTPException(
            status_code=400,
            detail=f"kind must be one of: {', '.join(sorted(VALID_KINDS))}",
        )
    contact = db.query(CustomerContact).filter(CustomerContact.id == payload.contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    data = payload.model_dump()
    data["kind"] = kind
    m = CustomerContactMethod(id=new_id(), **data)

    if m.is_primary:
        _clear_primary_same_kind(db, m.contact_id, m.kind)

    db.add(m)
    db.commit()
    db.refresh(m)
    return m


@router.put(
    "/customer-contact-methods/{method_id}",
    response_model=CustomerContactMethodOut,
)
def update_method(
    method_id: str,
    payload: CustomerContactMethodUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    m = db.query(CustomerContactMethod).filter(CustomerContactMethod.id == method_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Method not found")

    data = payload.model_dump(exclude_unset=True)
    if "kind" in data:
        kind = (data["kind"] or "").strip().lower() or "other"
        if kind not in VALID_KINDS:
            raise HTTPException(
                status_code=400,
                detail=f"kind must be one of: {', '.join(sorted(VALID_KINDS))}",
            )
        data["kind"] = kind

    if data.get("is_primary") is True:
        _clear_primary_same_kind(db, m.contact_id, data.get("kind") or m.kind)

    for k, v in data.items():
        setattr(m, k, v)

    db.add(m)
    db.commit()
    db.refresh(m)
    return m


@router.delete("/customer-contact-methods/{method_id}")
def delete_method(
    method_id: str,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    m = db.query(CustomerContactMethod).filter(CustomerContactMethod.id == method_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Method not found")
    db.delete(m)
    db.commit()
    return {"ok": True}
