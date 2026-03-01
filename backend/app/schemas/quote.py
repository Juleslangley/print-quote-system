from typing import Optional
from pydantic import BaseModel

class QuoteCreate(BaseModel):
    customer_id: str
    contact_id: Optional[str] = None
    notes_internal: str = ""
    # MIS-style: optional name, default_job_type (UI convenience when adding parts)
    name: Optional[str] = None
    default_job_type: Optional[str] = None

class QuotePatch(BaseModel):
    """PATCH quote. Triggers AUTO-UNLOCK if status is PRICED."""
    name: Optional[str] = None
    customer_id: Optional[str] = None
    contact_id: Optional[str] = None
    default_job_type: Optional[str] = None
    notes_internal: Optional[str] = None

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

    # MIS-style
    default_job_type: Optional[str] = None
    name: Optional[str] = None

    class Config:
        from_attributes = True


class QuotePartCreate(BaseModel):
    name: str = ""
    job_type: str  # required
    material_id: Optional[str] = None
    finished_w_mm: int
    finished_h_mm: int
    quantity: int = 1
    sides: int = 1
    preferred_sheet_size_id: Optional[str] = None
    waste_pct_override: Optional[float] = None
    setup_minutes_override: Optional[float] = None
    machine_key_override: Optional[str] = None


class QuotePartPatch(BaseModel):
    name: Optional[str] = None
    job_type: Optional[str] = None
    material_id: Optional[str] = None
    finished_w_mm: Optional[int] = None
    finished_h_mm: Optional[int] = None
    quantity: Optional[int] = None
    sides: Optional[int] = None
    preferred_sheet_size_id: Optional[str] = None
    waste_pct_override: Optional[float] = None
    setup_minutes_override: Optional[float] = None
    machine_key_override: Optional[str] = None


class QuotePartOut(BaseModel):
    id: str
    quote_id: str
    name: str
    job_type: str
    material_id: Optional[str] = None
    finished_w_mm: Optional[int] = None
    finished_h_mm: Optional[int] = None
    quantity: int
    sides: int
    preferred_sheet_size_id: Optional[str] = None
    waste_pct_override: Optional[float] = None
    setup_minutes_override: Optional[float] = None
    machine_key_override: Optional[str] = None

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
