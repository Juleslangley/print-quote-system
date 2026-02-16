from typing import Optional
from datetime import datetime
from pydantic import BaseModel, field_serializer


class PurchaseOrderCreate(BaseModel):
    supplier_id: str
    delivery_name: str = ""
    delivery_address: str = ""
    notes: str = ""
    internal_notes: str = ""


class PurchaseOrderUpdate(BaseModel):
    """Update payload. po_number is server-generated and immutable; if sent, API returns 400."""
    supplier_id: Optional[str] = None
    status: Optional[str] = None
    order_date: Optional[datetime] = None
    required_by: Optional[datetime] = None
    expected_by: Optional[datetime] = None
    delivery_name: Optional[str] = None
    delivery_address: Optional[str] = None
    notes: Optional[str] = None
    internal_notes: Optional[str] = None
    po_number: Optional[str] = None  # If present, endpoint returns 400


class PurchaseOrderOut(BaseModel):
    id: int
    po_number: Optional[str] = None
    supplier_id: str
    status: str
    currency: str
    order_date: Optional[datetime] = None
    required_by: Optional[datetime] = None
    expected_by: Optional[datetime] = None
    delivery_name: str
    delivery_address: str
    notes: str
    internal_notes: str
    subtotal_gbp: float
    vat_gbp: float
    total_gbp: float
    created_by_user_id: Optional[str] = None

    class Config:
        from_attributes = True

    @field_serializer("order_date", "required_by", "expected_by")
    def serialize_dt(self, v, _info):
        return v.isoformat() if v is not None else None


class SupplierSummary(BaseModel):
    id: str
    name: str
    email: str = ""
    phone: str = ""
    website: str = ""
    contact_person: str = ""
    accounts_email: str = ""
    account_ref: str = ""
    address: str = ""
    city: str = ""
    postcode: str = ""
    country: str = ""

    class Config:
        from_attributes = True


class CreatedByUser(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = ""

    class Config:
        from_attributes = True


class PurchaseOrderDetailOut(PurchaseOrderOut):
    """PO with supplier and created_by for header display."""
    supplier: Optional[SupplierSummary] = None
    created_by: Optional[CreatedByUser] = None
