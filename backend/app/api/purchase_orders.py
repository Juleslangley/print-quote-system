import logging
from typing import Optional
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.core.db import get_db

logger = logging.getLogger(__name__)
from app.api.permissions import require_admin, require_sales
from app.core.config import settings
from app.models.user import User
from app.models.supplier import Supplier
from app.models.purchase_order import PurchaseOrder
from app.models.purchase_order_line import PurchaseOrderLine
from app.models.material import Material
from app.models.material_size import MaterialSize
from app.models.document_render import DocumentRender
from app.models.file import File as FileRow
from app.models.base import new_id
from app.schemas.purchase_order import (
    PurchaseOrderCreate,
    PurchaseOrderUpdate,
    PurchaseOrderOut,
    PurchaseOrderDetailOut,
    SupplierSummary,
    CreatedByUser,
)
from app.schemas.purchase_order_line import PurchaseOrderLineCreate, PurchaseOrderLineOut
from app.services.pdfs.purchase_order_pdf import build_po_pdf
from app.services.purchase_order_workflow import transition_po_status
from pydantic import BaseModel as PydanticBase
from sqlalchemy import text

router = APIRouter()

VAT_RATE = 0.20

_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
UPLOADS_DIR = _BACKEND_ROOT / settings.UPLOADS_DIR


def _recalc_po_totals(db: Session, po_id: int) -> None:
    lines = (
        db.query(PurchaseOrderLine)
        .filter(PurchaseOrderLine.po_id == po_id, PurchaseOrderLine.active.is_(True))
        .all()
    )
    subtotal = sum(l.line_total_gbp for l in lines)
    vat = round(subtotal * VAT_RATE, 2)
    total = round(subtotal + vat, 2)
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if po:
        po.subtotal_gbp = subtotal
        po.vat_gbp = vat
        po.total_gbp = total
        db.add(po)


@router.get("/purchase-orders", response_model=list[PurchaseOrderOut])
def list_purchase_orders(
    status: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(require_sales),
):
    query = db.query(PurchaseOrder).order_by(
        PurchaseOrder.order_date.desc().nullslast(),
        PurchaseOrder.po_number.desc().nullslast(),
    )
    if status:
        query = query.filter(PurchaseOrder.status == status)
    if q and q.strip():
        ql = f"%{q.strip()}%"
        supplier_ids = db.query(Supplier.id).filter(Supplier.name.ilike(ql)).scalar_subquery()
        query = query.filter(
            (PurchaseOrder.po_number.ilike(ql)) | (PurchaseOrder.supplier_id.in_(supplier_ids))
        )
    return query.all()


class FromMaterialIn(PydanticBase):
    material_id: str
    qty: float = 1.0
    supplier_id: Optional[str] = None


@router.post("/purchase-orders/from-material", response_model=PurchaseOrderOut)
def create_po_from_material(
    payload: FromMaterialIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    """Create a draft PO with one line for the given material. Supplier from material if not provided."""
    mat = db.query(Material).filter(Material.id == payload.material_id).first()
    if not mat:
        raise HTTPException(status_code=404, detail="Material not found")
    supplier_id = payload.supplier_id or mat.supplier_id
    if not supplier_id and mat.supplier:
        sup = db.query(Supplier).filter(Supplier.name == mat.supplier).first()
        supplier_id = sup.id if sup else None
    if not supplier_id:
        raise HTTPException(status_code=400, detail="Material has no supplier. Set supplier on material first.")
    sup = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not sup:
        raise HTTPException(status_code=404, detail="Supplier not found")
    po = PurchaseOrder(
        supplier_id=supplier_id,
        status="draft",
        currency="GBP",
        delivery_name="",
        delivery_address="",
        notes="",
        internal_notes="",
        created_by_user_id=user.id if user else None,
    )
    db.add(po)
    db.flush()
    qty = max(0.0, float(payload.qty)) if payload.qty is not None else 1.0
    uom = "sheet" if (mat.type or "").lower() == "sheet" else "lm"
    unit_cost = 0.0
    first_size = (
        db.query(MaterialSize)
        .filter(MaterialSize.material_id == mat.id, MaterialSize.active.is_(True))
        .order_by(MaterialSize.sort_order.asc(), MaterialSize.width_mm.asc())
        .first()
    )
    if first_size:
        unit_cost = float(first_size.cost_per_sheet_gbp or first_size.cost_per_lm_gbp or 0)
    else:
        unit_cost = float(mat.cost_per_sheet_gbp or mat.cost_per_lm_gbp or 0)
    line_total = round(qty * unit_cost, 2)
    line = PurchaseOrderLine(
        id=new_id(),
        po_id=po.id,
        sort_order=0,
        material_id=mat.id,
        material_size_id=first_size.id if first_size else None,
        description=mat.name or "",
        supplier_product_code=mat.supplier_product_code or "",
        qty=qty,
        uom=uom,
        unit_cost_gbp=unit_cost,
        line_total_gbp=line_total,
    )
    db.add(line)
    db.flush()
    _recalc_po_totals(db, po.id)
    db.commit()
    db.refresh(po)
    return po


@router.post("/purchase-orders/clear-all", status_code=204)
def clear_all_purchase_orders(
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    """Remove all purchase orders and their lines from the database."""
    db.query(PurchaseOrderLine).delete(synchronize_session=False)
    db.query(PurchaseOrder).delete(synchronize_session=False)
    db.commit()
    return Response(status_code=204)


@router.post("/purchase-orders", response_model=PurchaseOrderOut)
def create_purchase_order(
    payload: PurchaseOrderCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    sup = db.query(Supplier).filter(Supplier.id == payload.supplier_id).first()
    if not sup:
        raise HTTPException(status_code=404, detail="Supplier not found")
    po = PurchaseOrder(
        supplier_id=payload.supplier_id,
        status="draft",
        delivery_name=payload.delivery_name or "",
        delivery_address=payload.delivery_address or "",
        notes=payload.notes or "",
        internal_notes=payload.internal_notes or "",
        created_by_user_id=user.id if user else None,
    )
    db.add(po)
    db.flush()  # Get id before commit so after_insert can set po_number
    db.commit()
    db.refresh(po)
    return po


@router.get("/purchase-orders/{po_id}", response_model=PurchaseOrderDetailOut)
def get_purchase_order(
    po_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_sales),
):
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    supplier = db.query(Supplier).filter(Supplier.id == po.supplier_id).first()
    created_by_user = (
        db.query(User).filter(User.id == po.created_by_user_id).first()
        if po.created_by_user_id else None
    )
    out = PurchaseOrderDetailOut.model_validate(po)
    out.supplier = SupplierSummary.model_validate(supplier) if supplier else None
    out.created_by = CreatedByUser.model_validate(created_by_user) if created_by_user else None
    return out


@router.delete("/purchase-orders/{po_id}", status_code=204)
def delete_purchase_order(
    po_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    """Delete a draft purchase order completely (and its lines). Only drafts can be deleted."""
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    if po.status != "draft":
        raise HTTPException(
            status_code=400,
            detail="Only draft purchase orders can be deleted. Finalized POs cannot be deleted.",
        )
    db.query(PurchaseOrderLine).filter(PurchaseOrderLine.po_id == po_id).delete(synchronize_session=False)
    db.delete(po)
    db.commit()
    return Response(status_code=204)


@router.post("/purchase-orders/{po_id}/promote", response_model=PurchaseOrderOut)
def promote_purchase_order(
    po_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    """Promote a draft PO to processed: transition status. po_number is already set from id on insert."""
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    if po.status != "draft":
        raise HTTPException(
            status_code=400,
            detail="Only draft purchase orders can be promoted",
        )
    transition_po_status(db, po, "processed", (user.id or None) if user else None)
    db.add(po)
    db.commit()
    db.refresh(po)
    return po


@router.get("/purchase-orders/{po_id}/lines", response_model=list[PurchaseOrderLineOut])
def list_po_lines(
    po_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_sales),
):
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    return (
        db.query(PurchaseOrderLine)
        .filter(PurchaseOrderLine.po_id == po_id)
        .order_by(PurchaseOrderLine.sort_order.asc(), PurchaseOrderLine.id.asc())
        .all()
    )


@router.delete("/purchase-orders/{po_id}/lines", status_code=204)
def delete_all_po_lines(
    po_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    """Remove all line entries for this purchase order (set active=False, same as single-line remove)."""
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    lines = db.query(PurchaseOrderLine).filter(PurchaseOrderLine.po_id == po_id).all()
    for line in lines:
        line.active = False
        db.add(line)
    if lines:
        _recalc_po_totals(db, po_id)
    db.commit()
    return Response(status_code=204)


@router.put("/purchase-orders/{po_id}", response_model=PurchaseOrderOut)
def update_purchase_order(
    po_id: int,
    payload: PurchaseOrderUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    if payload.po_number is not None:
        raise HTTPException(status_code=400, detail="po_number cannot be updated once created")
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    data = payload.model_dump(exclude_unset=True, exclude={"po_number"})
    requested_status = data.get("status") if "status" in data else None
    # Apply status transition via single source of truth (includes render hook)
    if requested_status is not None:
        allowed = {"draft", "processed", "sent", "part_received", "received", "cancelled"}
        status = str(requested_status).strip().lower()
        if status not in allowed:
            raise HTTPException(status_code=400, detail=f"status must be one of {allowed}")
        transition_po_status(db, po, status, user.id)
        # Remove status so the generic attribute setter doesn't overwrite status again
        data.pop("status", None)
    for k, v in data.items():
        if k == "po_number":
            continue
        setattr(po, k, v)
    db.add(po)
    db.commit()
    db.refresh(po)
    return po


@router.post("/purchase-orders/{po_id}/lines", response_model=PurchaseOrderLineOut)
def add_po_line(
    po_id: int,
    payload: PurchaseOrderLineCreate,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    line_total = round((payload.qty or 0) * (payload.unit_cost_gbp or 0), 2)
    line = PurchaseOrderLine(
        id=new_id(),
        po_id=po_id,
        sort_order=payload.sort_order,
        material_id=payload.material_id,
        material_size_id=payload.material_size_id,
        description=payload.description or "",
        supplier_product_code=payload.supplier_product_code or "",
        qty=payload.qty or 0,
        uom=payload.uom or "sheet",
        unit_cost_gbp=payload.unit_cost_gbp or 0,
        line_total_gbp=line_total,
    )
    db.add(line)
    db.flush()
    _recalc_po_totals(db, po_id)
    db.commit()
    db.refresh(line)
    return line


class StatusIn(PydanticBase):
    status: str


class ReceiveLineIn(PydanticBase):
    line_id: str
    receive_qty: float


class ReceiveIn(PydanticBase):
    lines: list[ReceiveLineIn]


@router.post("/purchase-orders/{po_id}/status", response_model=PurchaseOrderOut)
def set_po_status(
    request: Request,
    po_id: int,
    payload: StatusIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    # TODO-REMOVE: TEMP debug logging (this endpoint only sets status, not po_number)
    logger.info("PO status entry: %s %s | payload keys: %s", request.method, request.url.path, list(payload.model_dump().keys()))
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).with_for_update().first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    allowed = {"draft", "processed", "sent", "part_received", "received", "cancelled"}
    status = (payload.status or "").strip().lower()
    if status not in allowed:
        raise HTTPException(status_code=400, detail=f"status must be one of {allowed}")
    transition_po_status(db, po, status, user.id)
    db.add(po)
    db.commit()
    db.refresh(po)
    return po


@router.post("/purchase-orders/{po_id}/receive", response_model=PurchaseOrderOut)
def receive_po(
    request: Request,
    po_id: int,
    payload: ReceiveIn,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    # TODO-REMOVE: TEMP debug logging (this endpoint only sets status on PO, not po_number)
    logger.info("PO receive entry: %s %s | payload keys: %s", request.method, request.url.path, list(payload.model_dump().keys()))
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    for rec in payload.lines:
        line = db.query(PurchaseOrderLine).filter(
            PurchaseOrderLine.id == rec.line_id,
            PurchaseOrderLine.po_id == po_id,
        ).first()
        if line and rec.receive_qty > 0:
            line.received_qty = (line.received_qty or 0) + rec.receive_qty
            db.add(line)
    db.flush()
    lines = db.query(PurchaseOrderLine).filter(PurchaseOrderLine.po_id == po_id, PurchaseOrderLine.active.is_(True)).all()
    all_received = all((l.received_qty or 0) >= (l.qty or 0) for l in lines) and len(lines) > 0
    any_received = any((l.received_qty or 0) > 0 for l in lines)
    if all_received:
        po.status = "received"
    elif any_received:
        po.status = "part_received"
    db.add(po)
    db.commit()
    db.refresh(po)
    return po


@router.get("/purchase-orders/{po_id}.pdf")
def get_po_pdf(
    po_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_sales),
):
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")

    # Prefer the latest auto-rendered PO PDF (HTML template) when available.
    latest_render = (
        db.query(DocumentRender)
        .filter(DocumentRender.doc_type == "purchase_order", DocumentRender.entity_id == po_id)
        .order_by(DocumentRender.created_at.desc().nullslast())
        .first()
    )
    if latest_render:
        f = db.query(FileRow).filter(FileRow.id == latest_render.file_id).first()
        if f:
            path = UPLOADS_DIR / f.storage_key
            if path.exists():
                po_label = po.po_number or f"PO{po.id:07d}"
                filename = f"{po_label}.pdf"
                return Response(
                    content=path.read_bytes(),
                    media_type=f.mime or "application/pdf",
                    headers={"Content-Disposition": f"attachment; filename={filename}"},
                )

    pdf_bytes = build_po_pdf(db, po)
    po_label = po.po_number or f"PO{po.id:07d}"
    filename = f"{po_label}.pdf"
    return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename={filename}"})