from typing import Optional
from datetime import datetime
from pydantic import BaseModel, field_serializer


class SupplierInvoiceCreate(BaseModel):
    supplier_id: str
    invoice_number: Optional[str] = None
    invoice_date: Optional[datetime] = None
    currency: str = "GBP"
    subtotal_gbp: float = 0.0
    vat_gbp: float = 0.0
    total_gbp: float = 0.0


class SupplierInvoiceUpdate(BaseModel):
    invoice_number: Optional[str] = None
    invoice_date: Optional[datetime] = None
    currency: Optional[str] = None
    subtotal_gbp: Optional[float] = None
    vat_gbp: Optional[float] = None
    total_gbp: Optional[float] = None
    status: Optional[str] = None
    match_notes: Optional[str] = None


class SupplierInvoiceOut(BaseModel):
    id: str
    supplier_id: str
    invoice_number: str
    invoice_date: Optional[datetime] = None
    currency: str
    subtotal_gbp: float
    vat_gbp: float
    total_gbp: float
    status: str
    matched_po_id: Optional[str] = None
    match_confidence: float
    match_notes: str
    file_path: str
    raw_text: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

    @field_serializer("invoice_date", "created_at", "updated_at")
    def serialize_dt(self, v, _info):
        return v.isoformat() if v is not None else None
