from typing import Optional
from pydantic import BaseModel


class MachineRateCreate(BaseModel):
    machine_id: str
    operation_key: str
    unit: str  # sqm | lm | hour | sheet | job
    cost_per_unit_gbp: float = 0.0
    setup_minutes: float = 0.0
    setup_cost_gbp: float = 0.0
    min_charge_gbp: float = 0.0
    active: bool = True
    sort_order: int = 0
    notes: str = ""


class MachineRateUpdate(BaseModel):
    operation_key: Optional[str] = None
    unit: Optional[str] = None
    cost_per_unit_gbp: Optional[float] = None
    setup_minutes: Optional[float] = None
    setup_cost_gbp: Optional[float] = None
    min_charge_gbp: Optional[float] = None
    active: Optional[bool] = None
    sort_order: Optional[int] = None
    notes: Optional[str] = None


class MachineRateOut(BaseModel):
    id: str
    machine_id: str
    operation_key: str
    unit: str
    cost_per_unit_gbp: float
    setup_minutes: float
    setup_cost_gbp: float
    min_charge_gbp: float
    active: bool
    sort_order: int
    notes: str

    class Config:
        from_attributes = True
