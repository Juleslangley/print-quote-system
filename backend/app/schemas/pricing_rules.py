from typing import Optional
from pydantic import BaseModel

class TemplatePricingRuleCreate(BaseModel):
    template_id: str
    target_margin_pct: Optional[float] = None
    min_sell_gbp: Optional[float] = None
    sell_multiplier: float = 1.0
    margin_profile_id: Optional[str] = None
    active: bool = True
    meta: dict = {}

class TemplatePricingRuleUpdate(BaseModel):
    target_margin_pct: Optional[float] = None
    min_sell_gbp: Optional[float] = None
    sell_multiplier: Optional[float] = None
    margin_profile_id: Optional[str] = None
    active: Optional[bool] = None
    meta: Optional[dict] = None

class TemplatePricingRuleOut(BaseModel):
    id: str
    template_id: str
    target_margin_pct: Optional[float]
    min_sell_gbp: Optional[float]
    sell_multiplier: float
    margin_profile_id: Optional[str]
    active: bool
    meta: dict

    class Config:
        from_attributes = True


class CustomerPricingRuleCreate(BaseModel):
    customer_id: str
    category: Optional[str] = None
    template_id: Optional[str] = None
    margin_profile_id: Optional[str] = None
    target_margin_pct: Optional[float] = None
    min_sell_gbp: Optional[float] = None
    sell_multiplier: float = 1.0
    active: bool = True
    meta: dict = {}

class CustomerPricingRuleUpdate(BaseModel):
    category: Optional[str] = None
    template_id: Optional[str] = None
    margin_profile_id: Optional[str] = None
    target_margin_pct: Optional[float] = None
    min_sell_gbp: Optional[float] = None
    sell_multiplier: Optional[float] = None
    active: Optional[bool] = None
    meta: Optional[dict] = None

class CustomerPricingRuleOut(BaseModel):
    id: str
    customer_id: str
    category: Optional[str]
    template_id: Optional[str]
    margin_profile_id: Optional[str]
    target_margin_pct: Optional[float]
    min_sell_gbp: Optional[float]
    sell_multiplier: float
    active: bool
    meta: dict

    class Config:
        from_attributes = True
