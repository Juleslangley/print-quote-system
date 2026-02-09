from typing import Optional
from pydantic import BaseModel


class MaterialSizeCreate(BaseModel):
    material_id: str
    label: str
    width_mm: float
    height_mm: float
    cost_per_sheet_gbp: Optional[float] = None
    active: bool = True
    sort_order: int = 0


class MaterialSizeUpdate(BaseModel):
    label: Optional[str] = None
    width_mm: Optional[float] = None
    height_mm: Optional[float] = None
    cost_per_sheet_gbp: Optional[float] = None
    active: Optional[bool] = None
    sort_order: Optional[int] = None


class MaterialSizeOut(BaseModel):
    id: str
    material_id: str
    label: str
    width_mm: float
    height_mm: float
    cost_per_sheet_gbp: Optional[float] = None
    active: bool
    sort_order: int

    class Config:
        from_attributes = True
