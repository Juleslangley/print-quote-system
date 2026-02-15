from typing import Optional
from pydantic import BaseModel

class SupplierCreate(BaseModel):
    name: str
    supplier_id: Optional[str] = None
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
    lead_time_days_default: int = 0
    notes: str = ""
    active: bool = True

class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    supplier_id: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    contact_person: Optional[str] = None
    accounts_email: Optional[str] = None
    account_ref: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    postcode: Optional[str] = None
    country: Optional[str] = None
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
    contact_person: str
    accounts_email: str
    account_ref: str
    address: str
    city: str
    postcode: str
    country: str
    lead_time_days_default: int
    notes: str
    active: bool

    class Config:
        from_attributes = True
