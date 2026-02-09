from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.api.permissions import require_admin
from app.models.purchase_order import PurchaseOrder
from app.models.purchase_order_line import PurchaseOrderLine
from app.schemas.purchase_order_line import PurchaseOrderLineUpdate, PurchaseOrderLineOut
from app.api.purchase_orders import _recalc_po_totals

router = APIRouter()


@router.put("/purchase-order-lines/{line_id}", response_model=PurchaseOrderLineOut)
def update_po_line(
    line_id: str,
    payload: PurchaseOrderLineUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    line = db.query(PurchaseOrderLine).filter(PurchaseOrderLine.id == line_id).first()
    if not line:
        raise HTTPException(status_code=404, detail="Line not found")
    data = payload.model_dump(exclude_unset=True)
    if "qty" in data or "unit_cost_gbp" in data:
        qty = data.get("qty", line.qty)
        unit_cost = data.get("unit_cost_gbp", line.unit_cost_gbp)
        data["line_total_gbp"] = round((qty or 0) * (unit_cost or 0), 2)
    for k, v in data.items():
        setattr(line, k, v)
    db.add(line)
    db.flush()
    _recalc_po_totals(db, line.po_id)
    db.commit()
    db.refresh(line)
    return line


@router.delete("/purchase-order-lines/{line_id}", response_model=PurchaseOrderLineOut)
def delete_po_line(
    line_id: str,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    line = db.query(PurchaseOrderLine).filter(PurchaseOrderLine.id == line_id).first()
    if not line:
        raise HTTPException(status_code=404, detail="Line not found")
    line.active = False
    db.add(line)
    db.flush()
    _recalc_po_totals(db, line.po_id)
    db.commit()
    db.refresh(line)
    return line
