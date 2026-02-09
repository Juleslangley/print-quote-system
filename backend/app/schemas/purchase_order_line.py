from typing import Optional
from pydantic import BaseModel


class PurchaseOrderLineCreate(BaseModel):
    po_id: str
    material_id: Optional[str] = None
    material_size_id: Optional[str] = None
    description: str = ""
    supplier_product_code: str = ""
    qty: float = 0.0
    uom: str = "sheet"
    unit_cost_gbp: float = 0.0
    sort_order: int = 0


class PurchaseOrderLineUpdate(BaseModel):
    material_id: Optional[str] = None
    material_size_id: Optional[str] = None
    description: Optional[str] = None
    supplier_product_code: Optional[str] = None
    qty: Optional[float] = None
    uom: Optional[str] = None
    unit_cost_gbp: Optional[float] = None
    sort_order: Optional[int] = None
    received_qty: Optional[float] = None


class PurchaseOrderLineOut(BaseModel):
    id: str
    po_id: str
    sort_order: int
    material_id: Optional[str] = None
    material_size_id: Optional[str] = None
    description: str
    supplier_product_code: str
    qty: float
    uom: str
    unit_cost_gbp: float
    line_total_gbp: float
    received_qty: float
    active: bool

    class Config:
        from_attributes = True
