from typing import Optional
from pydantic import BaseModel


class EmployerCreate(BaseModel):
    name: str
    contact_name: str = ""
    email: str = ""
    phone: str = ""
    role: str = ""
    notes: str = ""
    active: bool = True


class EmployerUpdate(BaseModel):
    name: Optional[str] = None
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[str] = None
    notes: Optional[str] = None
    active: Optional[bool] = None


class EmployerOut(BaseModel):
    id: str
    name: str
    contact_name: str
    email: str
    phone: str
    role: str
    notes: str
    active: bool

    class Config:
        from_attributes = True
