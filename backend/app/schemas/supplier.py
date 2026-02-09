from typing import Optional
from pydantic import BaseModel

class SupplierCreate(BaseModel):
    name: str
    supplier_id: Optional[str] = None
    email: str = ""
    phone: str = ""
    website: str = ""
    account_ref: str = ""
    lead_time_days_default: int = 0
    notes: str = ""
    active: bool = True

class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    supplier_id: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    account_ref: Optional[str] = None
    lead_time_days_default: Optional[int] = None
    notes: Optional[str] = None
    active: Optional[bool] = None

class SupplierOut(BaseModel):
    id: str
    name: str
    supplier_id: Optional[str]
    email: str
    phone: str
    website: str
    account_ref: str
    lead_time_days_default: int
    notes: str
    active: bool

    class Config:
        from_attributes = True
