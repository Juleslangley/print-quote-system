from typing import Optional
from pydantic import BaseModel


class CustomerContactMethodCreate(BaseModel):
    contact_id: str
    kind: str  # phone, email, whatsapp, other
    label: str = ""
    value: str = ""
    is_primary: bool = False
    can_sms: bool = False
    can_whatsapp: bool = False
    active: bool = True
    sort_order: int = 0


class CustomerContactMethodUpdate(BaseModel):
    kind: Optional[str] = None
    label: Optional[str] = None
    value: Optional[str] = None
    is_primary: Optional[bool] = None
    can_sms: Optional[bool] = None
    can_whatsapp: Optional[bool] = None
    active: Optional[bool] = None
    sort_order: Optional[int] = None


class CustomerContactMethodOut(BaseModel):
    id: str
    contact_id: str
    kind: str
    label: Optional[str] = ""
    value: Optional[str] = ""
    is_primary: bool
    can_sms: bool
    can_whatsapp: bool
    active: bool
    sort_order: int

    class Config:
        from_attributes = True
