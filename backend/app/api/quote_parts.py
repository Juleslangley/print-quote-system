"""MIS-style quote parts API. Using new_id from app.models.base."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.base import new_id
from app.models.quote import Quote
from app.models.quote_part import QuotePart
from app.schemas.quote import QuotePartCreate, QuotePartPatch, QuotePartOut
from app.api.permissions import require_sales
from app.services.mis_pricing import price_quote

router = APIRouter()


def _auto_unlock_if_priced(db: Session, quote_id: str) -> None:
    """If quote status is priced, set to draft. Snapshots are never deleted."""
    q = db.query(Quote).filter(Quote.id == quote_id).first()
    if q and q.status and str(q.status).lower() == "priced":
        q.status = "draft"
        db.add(q)


@router.post("/quotes/{quote_id}/parts", response_model=QuotePartOut)
def create_part(
    quote_id: str,
    payload: QuotePartCreate,
    db: Session = Depends(get_db),
    _=Depends(require_sales),
):
    q = db.query(Quote).filter(Quote.id == quote_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Quote not found")
    _auto_unlock_if_priced(db, quote_id)

    part = QuotePart(
        id=new_id(),
        quote_id=quote_id,
        name=payload.name or "",
        job_type=payload.job_type,
        material_id=payload.material_id,
        finished_w_mm=payload.finished_w_mm,
        finished_h_mm=payload.finished_h_mm,
        quantity=payload.quantity,
        sides=payload.sides,
        preferred_sheet_size_id=payload.preferred_sheet_size_id,
        waste_pct_override=payload.waste_pct_override,
        setup_minutes_override=payload.setup_minutes_override,
        machine_key_override=payload.machine_key_override,
    )
    db.add(part)
    db.commit()
    db.refresh(part)
    return part


@router.patch("/quote-parts/{part_id}", response_model=QuotePartOut)
def update_part(
    part_id: str,
    payload: QuotePartPatch,
    db: Session = Depends(get_db),
    _=Depends(require_sales),
):
    part = db.query(QuotePart).filter(QuotePart.id == part_id).first()
    if not part:
        raise HTTPException(status_code=404, detail="Part not found")
    _auto_unlock_if_priced(db, part.quote_id)

    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(part, k, v)
    db.add(part)
    db.commit()
    db.refresh(part)
    return part


@router.delete("/quote-parts/{part_id}")
def delete_part(
    part_id: str,
    db: Session = Depends(get_db),
    _=Depends(require_sales),
):
    part = db.query(QuotePart).filter(QuotePart.id == part_id).first()
    if not part:
        raise HTTPException(status_code=404, detail="Part not found")
    quote_id = part.quote_id
    _auto_unlock_if_priced(db, quote_id)
    db.delete(part)
    db.commit()
    return {"ok": True}


@router.get("/quotes/{quote_id}/parts", response_model=list[QuotePartOut])
def list_parts(
    quote_id: str,
    db: Session = Depends(get_db),
    _=Depends(require_sales),
):
    q = db.query(Quote).filter(Quote.id == quote_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Quote not found")
    return db.query(QuotePart).filter(QuotePart.quote_id == quote_id).order_by(QuotePart.id).all()


@router.post("/quote-parts/{part_id}/calculate")
def calculate_part(
    part_id: str,
    db: Session = Depends(get_db),
    _=Depends(require_sales),
):
    """Calls price_quote and returns only this part's slice + quote totals + input_hash.
    The `part` dict includes `production` (machine_name, quantities, rates_applied, time, warnings)
    from app.services.mis_pricing._price_part when implemented."""
    part = db.query(QuotePart).filter(QuotePart.id == part_id).first()
    if not part:
        raise HTTPException(status_code=404, detail="Part not found")
    result = price_quote(db, part.quote_id)
    part_slice = next((p for p in result["parts"] if p["part_id"] == part_id), None)
    return {
        "part": part_slice,
        "totals": result["totals"],
        "totals_by_lane": result["totals_by_lane"],
        "input_hash": result["input_hash"],
        "pricing_version": result["pricing_version"],
        "warnings": result["warnings"],
    }
