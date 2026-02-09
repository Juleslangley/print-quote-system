import logging
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.core.db import get_db
from app.api.permissions import require_admin
from app.models.supplier_invoice import SupplierInvoice
from app.models.supplier import Supplier
from app.models.purchase_order import PurchaseOrder
from app.models.base import new_id
from app.schemas.supplier_invoice import SupplierInvoiceCreate, SupplierInvoiceUpdate, SupplierInvoiceOut

logger = logging.getLogger(__name__)
router = APIRouter()

# backend/app/api -> backend/app -> backend
_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
UPLOADS_DIR = _BACKEND_ROOT / "uploads" / "invoices"
MATCH_TOLERANCE_GBP = 1.00

# Prefer PO status order for scoring (higher = better)
_STATUS_ORDER = {"received": 3, "part_received": 2, "sent": 1, "draft": 0}


def _ensure_uploads_dir():
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


@router.get("/supplier-invoices", response_model=list[SupplierInvoiceOut])
def list_supplier_invoices(
    q: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    supplier_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    query = db.query(SupplierInvoice).order_by(SupplierInvoice.created_at.desc())
    if status and status.strip():
        query = query.filter(SupplierInvoice.status == status.strip())
    if supplier_id and supplier_id.strip():
        query = query.filter(SupplierInvoice.supplier_id == supplier_id.strip())
    if q and q.strip():
        ql = f"%{q.strip()}%"
        query = query.filter(
            (SupplierInvoice.invoice_number.ilike(ql))
            | (SupplierInvoice.id.ilike(ql))
        )
    return query.all()


@router.post("/supplier-invoices/upload", response_model=SupplierInvoiceOut)
async def upload_supplier_invoice(
    file: UploadFile = File(...),
    supplier_id: str = Form(...),
    invoice_number: str = Form(""),
    invoice_date: Optional[str] = Form(None),
    subtotal_gbp: float = Form(0.0),
    vat_gbp: float = Form(0.0),
    total_gbp: float = Form(0.0),
    currency: str = Form("GBP"),
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    sup = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not sup:
        raise HTTPException(status_code=404, detail="Supplier not found")
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="PDF file required")

    inv_id = new_id()
    _ensure_uploads_dir()
    file_path_rel = f"invoices/{inv_id}.pdf"
    dest = UPLOADS_DIR / f"{inv_id}.pdf"
    content = await file.read()
    dest.write_bytes(content)

    from datetime import datetime as dt
    inv_date = None
    if invoice_date and invoice_date.strip():
        try:
            inv_date = dt.fromisoformat(invoice_date.strip().replace("Z", "+00:00"))
        except ValueError:
            pass

    inv = SupplierInvoice(
        id=inv_id,
        supplier_id=supplier_id,
        invoice_number=(invoice_number or "").strip(),
        invoice_date=inv_date,
        currency=currency or "GBP",
        subtotal_gbp=float(subtotal_gbp),
        vat_gbp=float(vat_gbp),
        total_gbp=float(total_gbp),
        status="uploaded",
        file_path=file_path_rel,
    )
    db.add(inv)
    db.flush()

    # Duplicate detection: allow but flag
    if inv.invoice_number:
        dup = (
            db.query(SupplierInvoice)
            .filter(
                and_(
                    SupplierInvoice.supplier_id == supplier_id,
                    SupplierInvoice.invoice_number == inv.invoice_number,
                    SupplierInvoice.id != inv.id,
                )
            )
            .first()
        )
        if dup:
            inv.status = "duplicate"
            inv.match_notes = f"Possible duplicate of invoice {dup.id}"
    db.commit()
    db.refresh(inv)
    return inv


@router.get("/supplier-invoices/{invoice_id}", response_model=SupplierInvoiceOut)
def get_supplier_invoice(
    invoice_id: str,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    inv = db.query(SupplierInvoice).filter(SupplierInvoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Supplier invoice not found")
    return inv


@router.put("/supplier-invoices/{invoice_id}", response_model=SupplierInvoiceOut)
def update_supplier_invoice(
    invoice_id: str,
    payload: SupplierInvoiceUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    inv = db.query(SupplierInvoice).filter(SupplierInvoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Supplier invoice not found")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(inv, k, v)
    # Duplicate check on update when invoice_number is set
    if inv.invoice_number and "invoice_number" in data:
        dup = (
            db.query(SupplierInvoice)
            .filter(
                and_(
                    SupplierInvoice.supplier_id == inv.supplier_id,
                    SupplierInvoice.invoice_number == inv.invoice_number,
                    SupplierInvoice.id != inv.id,
                )
            )
            .first()
        )
        if dup:
            inv.status = "duplicate"
            inv.match_notes = inv.match_notes or f"Possible duplicate of invoice {dup.id}"
    db.add(inv)
    db.commit()
    db.refresh(inv)
    return inv


@router.get("/supplier-invoices/{invoice_id}/candidates")
def get_invoice_candidates(
    invoice_id: str,
    tolerance: float = Query(MATCH_TOLERANCE_GBP, description="GBP tolerance for total match"),
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    inv = db.query(SupplierInvoice).filter(SupplierInvoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Supplier invoice not found")

    pos = (
        db.query(PurchaseOrder)
        .filter(
            PurchaseOrder.supplier_id == inv.supplier_id,
            PurchaseOrder.status != "cancelled",
        )
        .order_by(PurchaseOrder.order_date.desc().nullslast(), PurchaseOrder.po_number.desc())
        .all()
    )
    candidates = []
    for po in pos:
        total_diff = abs((inv.total_gbp or 0) - (po.total_gbp or 0))
        score = 0.0
        reasons = []
        if total_diff <= tolerance:
            score += 80
            reasons.append("total within tolerance")
        else:
            score += max(0, 40 - total_diff)
            reasons.append(f"total diff £{total_diff:.2f}")
        status_rank = _STATUS_ORDER.get(po.status, 0)
        score += status_rank * 5
        reasons.append(f"status={po.status}")
        candidates.append({
            "po_id": po.id,
            "po_number": po.po_number,
            "po_total": po.total_gbp,
            "total_diff": round(total_diff, 2),
            "status": po.status,
            "score": round(score, 1),
            "reason": "; ".join(reasons),
        })
    candidates.sort(key=lambda x: (-x["score"], x["total_diff"]))
    return {"candidates": candidates[:5]}


from pydantic import BaseModel as _PydanticBase


class MatchIn(_PydanticBase):
    po_id: str


@router.post("/supplier-invoices/{invoice_id}/match", response_model=SupplierInvoiceOut)
def confirm_match(
    invoice_id: str,
    payload: MatchIn,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    po_id = payload.po_id
    if not po_id:
        raise HTTPException(status_code=400, detail="po_id required")
    inv = db.query(SupplierInvoice).filter(SupplierInvoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Supplier invoice not found")
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    if po.supplier_id != inv.supplier_id:
        raise HTTPException(status_code=400, detail="Purchase order supplier does not match invoice supplier")

    total_diff = abs((inv.total_gbp or 0) - (po.total_gbp or 0))
    inv.matched_po_id = po_id
    inv.match_confidence = 1.0
    if total_diff > MATCH_TOLERANCE_GBP:
        inv.status = "mismatch"
        inv.match_notes = f"Totals differ by £{total_diff:.2f} (invoice £{inv.total_gbp:.2f}, PO £{po.total_gbp:.2f})"
    else:
        inv.status = "matched"
        inv.match_notes = inv.match_notes or ""
    db.add(inv)
    db.commit()
    db.refresh(inv)
    return inv


@router.get("/supplier-invoices/{invoice_id}.pdf")
def get_invoice_pdf(
    invoice_id: str,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    inv = db.query(SupplierInvoice).filter(SupplierInvoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Supplier invoice not found")
    if not inv.file_path:
        raise HTTPException(status_code=404, detail="No file attached")
    # file_path is stored as "invoices/<id>.pdf"
    local_path = UPLOADS_DIR / f"{invoice_id}.pdf"
    if not local_path.is_file():
        raise HTTPException(status_code=404, detail="File not found on disk")
    return FileResponse(local_path, media_type="application/pdf", filename=f"invoice-{invoice_id}.pdf")
