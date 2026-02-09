from typing import Optional
from pydantic import BaseModel

class RateCreate(BaseModel):
    rate_type: str
    setup_minutes: float = 10.0
    hourly_cost_gbp: float = 35.0
    run_speed: dict = {}
    active: bool = True

class RateUpdate(BaseModel):
    rate_type: Optional[str] = None
    setup_minutes: Optional[float] = None
    hourly_cost_gbp: Optional[float] = None
    run_speed: Optional[dict] = None
    active: Optional[bool] = None

class RateOut(BaseModel):
    id: str
    rate_type: str
    setup_minutes: float
    hourly_cost_gbp: float
    run_speed: dict
    active: bool

    class Config:
        from_attributes = True
