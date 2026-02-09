from typing import Optional
from pydantic import BaseModel

class QuoteCreate(BaseModel):
    customer_id: str
    contact_id: Optional[str] = None
    notes_internal: str = ""

class QuoteUpdateCommercial(BaseModel):
    margin_profile_id: Optional[str] = None
    target_margin_pct: Optional[float] = None
    discount_pct: Optional[float] = None
    rounding_override: Optional[dict] = None
    totals_locked: Optional[bool] = None

class QuoteOut(BaseModel):
    id: str
    quote_number: str
    customer_id: str
    contact_id: Optional[str] = None
    status: str
    pricing_version: str
    notes_internal: str
    subtotal_sell: float
    vat: float
    total_sell: float

    margin_profile_id: Optional[str] = None
    target_margin_pct: Optional[float] = None
    discount_pct: Optional[float] = 0.0
    rounding_override: Optional[dict] = None
    totals_locked: Optional[bool] = False

    class Config:
        from_attributes = True


class QuoteItemCreate(BaseModel):
    template_id: str
    title: str
    qty: int
    width_mm: float
    height_mm: float
    sides: int = 1
    options: dict = {}

class QuoteItemCommercialUpdate(BaseModel):
    sell_locked: Optional[bool] = None
    manual_sell_total: Optional[float] = None
    manual_discount_pct: Optional[float] = None
    manual_reason: Optional[str] = None

class QuoteItemOut(BaseModel):
    id: str
    quote_id: str
    template_id: str
    title: str
    qty: int
    width_mm: float
    height_mm: float
    sides: int
    options: dict

    cost_total: float
    sell_total: float
    margin_pct: float
    calc_snapshot: dict

    sell_locked: bool
    manual_sell_total: Optional[float]
    manual_discount_pct: float
    manual_reason: str

    class Config:
        from_attributes = True
