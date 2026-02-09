from typing import Optional
from pydantic import BaseModel, Field


class CustomerCreate(BaseModel):
    name: str
    email: str = ""
    phone: str = ""
    website: str = ""

    billing_name: str = ""
    billing_email: str = ""
    billing_phone: str = ""
    billing_address: str = ""

    vat_number: str = ""
    account_ref: str = ""
    notes: str = ""

    meta: dict = Field(default_factory=dict)
    active: bool = True

    default_margin_profile_id: Optional[str] = None


class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None

    billing_name: Optional[str] = None
    billing_email: Optional[str] = None
    billing_phone: Optional[str] = None
    billing_address: Optional[str] = None

    vat_number: Optional[str] = None
    account_ref: Optional[str] = None
    notes: Optional[str] = None

    meta: Optional[dict] = None
    active: Optional[bool] = None

    default_margin_profile_id: Optional[str] = None


class CustomerOut(BaseModel):
    id: str
    name: str
    email: Optional[str] = ""
    phone: Optional[str] = ""
    website: Optional[str] = ""

    billing_name: Optional[str] = ""
    billing_email: Optional[str] = ""
    billing_phone: Optional[str] = ""
    billing_address: Optional[str] = ""

    vat_number: Optional[str] = ""
    account_ref: Optional[str] = ""
    notes: Optional[str] = ""

    meta: Optional[dict] = None
    active: Optional[bool] = True

    default_margin_profile_id: Optional[str] = None

    class Config:
        from_attributes = True
