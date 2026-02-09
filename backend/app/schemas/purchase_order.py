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
    supplier_id: Optional[str] = None
    status: Optional[str] = None
    order_date: Optional[datetime] = None
    required_by: Optional[datetime] = None
    expected_by: Optional[datetime] = None
    delivery_name: Optional[str] = None
    delivery_address: Optional[str] = None
    notes: Optional[str] = None
    internal_notes: Optional[str] = None


class PurchaseOrderOut(BaseModel):
    id: str
    po_number: str
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
