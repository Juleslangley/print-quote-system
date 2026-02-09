from typing import Optional
from pydantic import BaseModel

class MarginProfileCreate(BaseModel):
    name: str
    target_margin_pct: float = 0.40
    min_margin_pct: float = 0.25
    min_sell_gbp: float = 0.0
    rounding: dict = {"mode": "NEAREST", "step": 0.01}
    active: bool = True

class MarginProfileUpdate(BaseModel):
    name: Optional[str] = None
    target_margin_pct: Optional[float] = None
    min_margin_pct: Optional[float] = None
    min_sell_gbp: Optional[float] = None
    rounding: Optional[dict] = None
    active: Optional[bool] = None

class MarginProfileOut(BaseModel):
    id: str
    name: str
    target_margin_pct: float
    min_margin_pct: float
    min_sell_gbp: float
    rounding: dict
    active: bool

    class Config:
        from_attributes = True
