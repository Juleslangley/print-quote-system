from typing import Optional
from pydantic import BaseModel, field_validator

class MaterialCreate(BaseModel):
    name: str
    nominal_code: str = ""
    supplier_product_code: str = ""
    type: str  # sheet/roll

    # legacy string supplier (keep)
    supplier: str = ""

    # FK supplier id (optional)
    supplier_id: Optional[str] = None

    cost_per_sheet_gbp: Optional[float] = None
    sheet_width_mm: Optional[float] = None
    sheet_height_mm: Optional[float] = None
    cost_per_lm_gbp: Optional[float] = None
    roll_width_mm: Optional[float] = None
    min_billable_lm: Optional[float] = None
    custom_length_available: bool = False
    waste_pct_default: float = 0.05
    active: bool = True  # for admin toggles
    meta: dict = {}
    allowed_job_types: Optional[list[str]] = None


class MaterialUpdate(BaseModel):
    name: Optional[str] = None
    nominal_code: Optional[str] = None
    supplier_product_code: Optional[str] = None
    type: Optional[str] = None

    supplier: Optional[str] = None
    supplier_id: Optional[str] = None

    cost_per_sheet_gbp: Optional[float] = None
    sheet_width_mm: Optional[float] = None
    sheet_height_mm: Optional[float] = None
    cost_per_lm_gbp: Optional[float] = None
    roll_width_mm: Optional[float] = None
    min_billable_lm: Optional[float] = None
    custom_length_available: Optional[bool] = None
    waste_pct_default: Optional[float] = None
    active: Optional[bool] = None
    meta: Optional[dict] = None
    allowed_job_types: Optional[list[str]] = None


class MaterialOut(BaseModel):
    id: str
    name: str
    nominal_code: str = ""
    supplier_product_code: str = ""
    type: str

    supplier: str
    supplier_id: Optional[str]

    cost_per_sheet_gbp: Optional[float]
    sheet_width_mm: Optional[float]
    sheet_height_mm: Optional[float]
    cost_per_lm_gbp: Optional[float]
    roll_width_mm: Optional[float]
    min_billable_lm: Optional[float]
    custom_length_available: bool = False
    waste_pct_default: float
    active: bool
    meta: dict = {}
    allowed_job_types: list[str] = []

    @field_validator("nominal_code", "supplier_product_code", "supplier", mode="before")
    @classmethod
    def empty_str_default(cls, v):
        return v if v is not None else ""

    @field_validator("meta", mode="before")
    @classmethod
    def meta_dict(cls, v):
        return v if isinstance(v, dict) else {}

    class Config:
        from_attributes = True
