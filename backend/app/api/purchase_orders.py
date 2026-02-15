from email.message import EmailMessage
import smtplib

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.core.config import settings
from app.api.permissions import require_admin, require_sales
from app.models.user import User
from app.models.supplier import Supplier
from app.models.purchase_order import PurchaseOrder
from app.models.purchase_order_line import PurchaseOrderLine
from app.models.po_sequence import POSequence
from app.models.base import new_id
from app.schemas.purchase_order import PurchaseOrderCreate, PurchaseOrderUpdate, PurchaseOrderOut
from app.schemas.purchase_order_line import PurchaseOrderLineCreate, PurchaseOrderLineOut
from app.services.pdfs.purchase_order_pdf import build_po_pdf
from pydantic import BaseModel as PydanticBase

router = APIRouter()

VAT_RATE = 0.20


def _send_po_email(to_email: str, subject: str, body: str, pdf_bytes: bytes, filename: str) -> None:
    if not settings.SMTP_HOST or not settings.SMTP_FROM_EMAIL:
        raise HTTPException(
            status_code=400,
            detail="SMTP is not configured. Set SMTP_HOST and SMTP_FROM_EMAIL.",
        )

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM_EMAIL
    msg["To"] = to_email
    msg.set_content(body)
    msg.add_attachment(
        pdf_bytes,
        maintype="application",
        subtype="pdf",
        filename=filename,
    )

    try:
        if settings.SMTP_USE_SSL:
            with smtplib.SMTP_SSL(
                host=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                timeout=settings.SMTP_TIMEOUT_SECONDS,
            ) as smtp:
                if settings.SMTP_USERNAME:
                    smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                smtp.send_message(msg)
            return

        with smtplib.SMTP(
            host=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            timeout=settings.SMTP_TIMEOUT_SECONDS,
        ) as smtp:
            smtp.ehlo()
            if settings.SMTP_USE_TLS:
                smtp.starttls()
                smtp.ehlo()
            if settings.SMTP_USERNAME:
                smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            smtp.send_message(msg)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to send email: {exc}") from exc


def _next_po_number(db: Session) -> str:
    row = db.query(POSequence).filter(POSequence.name == "default").with_for_update().first()
    if not row:
        db.add(POSequence(name="default", next_val=1))
        db.flush()
        n = 1
    else:
        n = row.next_val
        row.next_val = n + 1
    db.flush()
    return f"PO{n:07d}"


def _recalc_po_totals(db: Session, po_id: str) -> None:
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
    status: str | None = Query(None),
    q: str | None = Query(None),
    db: Session = Depends(get_db),
    _=Depends(require_sales),
):
    query = db.query(PurchaseOrder).order_by(PurchaseOrder.order_date.desc().nullslast(), PurchaseOrder.po_number.desc())
    if status:
        query = query.filter(PurchaseOrder.status == status)
    if q and q.strip():
        ql = f"%{q.strip()}%"
        supplier_ids = db.query(Supplier.id).filter(Supplier.name.ilike(ql)).scalar_subquery()
        query = query.filter(
            (PurchaseOrder.po_number.ilike(ql)) | (PurchaseOrder.supplier_id.in_(supplier_ids))
        )
    return query.all()


@router.post("/purchase-orders", response_model=PurchaseOrderOut)
def create_purchase_order(
    payload: PurchaseOrderCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    sup = db.query(Supplier).filter(Supplier.id == payload.supplier_id).first()
    if not sup:
        raise HTTPException(status_code=404, detail="Supplier not found")
    po_number = _next_po_number(db)
    po = PurchaseOrder(
        id=new_id(),
        po_number=po_number,
        supplier_id=payload.supplier_id,
        status="draft",
        delivery_name=payload.delivery_name or "",
        delivery_address=payload.delivery_address or "",
        notes=payload.notes or "",
        internal_notes=payload.internal_notes or "",
        created_by_user_id=user.id,
    )
    db.add(po)
    db.commit()
    db.refresh(po)
    return po


@router.get("/purchase-orders/{po_id}", response_model=PurchaseOrderOut)
def get_purchase_order(
    po_id: str,
    db: Session = Depends(get_db),
    _=Depends(require_sales),
):
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    return po


@router.get("/purchase-orders/{po_id}/lines", response_model=list[PurchaseOrderLineOut])
def list_po_lines(
    po_id: str,
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


@router.put("/purchase-orders/{po_id}", response_model=PurchaseOrderOut)
def update_purchase_order(
    po_id: str,
    payload: PurchaseOrderUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(po, k, v)
    db.add(po)
    db.commit()
    db.refresh(po)
    return po


@router.post("/purchase-orders/{po_id}/lines", response_model=PurchaseOrderLineOut)
def add_po_line(
    po_id: str,
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


class EmailPOIn(PydanticBase):
    to_email: str | None = None
    subject: str | None = None
    message: str | None = None


@router.post("/purchase-orders/{po_id}/status", response_model=PurchaseOrderOut)
def set_po_status(
    po_id: str,
    payload: StatusIn,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    allowed = {"draft", "sent", "part_received", "received", "cancelled"}
    if payload.status not in allowed:
        raise HTTPException(status_code=400, detail=f"status must be one of {allowed}")
    po.status = payload.status
    db.add(po)
    db.commit()
    db.refresh(po)
    return po


@router.post("/purchase-orders/{po_id}/receive", response_model=PurchaseOrderOut)
def receive_po(
    po_id: str,
    payload: ReceiveIn,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
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
    po_id: str,
    db: Session = Depends(get_db),
    _=Depends(require_sales),
):
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    pdf_bytes = build_po_pdf(db, po)
    return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename={po.po_number}.pdf"})


@router.post("/purchase-orders/{po_id}/email")
def email_po(
    po_id: str,
    payload: EmailPOIn,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")

    supplier = db.query(Supplier).filter(Supplier.id == po.supplier_id).first()
    recipient = (payload.to_email or (supplier.email if supplier else "")).strip()
    if not recipient:
        raise HTTPException(status_code=400, detail="Recipient email is required")

    subject = (payload.subject or "").strip() or f"Purchase Order {po.po_number}"
    body = (payload.message or "").strip() or (
        f"Please find attached purchase order {po.po_number}.\n\n"
        "Regards"
    )
    pdf_bytes = build_po_pdf(db, po)
    _send_po_email(
        to_email=recipient,
        subject=subject,
        body=body,
        pdf_bytes=pdf_bytes,
        filename=f"{po.po_number}.pdf",
    )

    return {"ok": True, "to_email": recipient}