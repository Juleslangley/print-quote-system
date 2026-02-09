from typing import Optional
from pydantic import BaseModel


class CustomerContactCreate(BaseModel):
    customer_id: str
    first_name: str = ""
    last_name: str = ""
    job_title: str = ""
    department: str = ""
    name: str = ""
    email: str = ""
    phone: str = ""
    mobile_phone: str = ""
    role: str = ""
    notes: str = ""
    is_primary: bool = False
    active: bool = True
    sort_order: int = 0


class CustomerContactUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    job_title: Optional[str] = None
    department: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    mobile_phone: Optional[str] = None
    role: Optional[str] = None
    notes: Optional[str] = None
    is_primary: Optional[bool] = None
    active: Optional[bool] = None
    sort_order: Optional[int] = None


class CustomerContactOut(BaseModel):
    id: str
    customer_id: str
    first_name: Optional[str] = ""
    last_name: Optional[str] = ""
    job_title: Optional[str] = ""
    department: Optional[str] = ""
    name: Optional[str] = ""
    email: Optional[str] = ""
    phone: Optional[str] = ""
    mobile_phone: Optional[str] = ""
    role: Optional[str] = ""
    notes: Optional[str] = ""
    is_primary: bool
    active: bool
    sort_order: int

    class Config:
        from_attributes = True
