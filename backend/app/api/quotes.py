from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.core.config import settings
from app.models.base import new_id
from app.models.quote import Quote, QuoteItem
from app.models.customer import Customer
from app.models.template import ProductTemplate
from app.models.material import Material
from app.models.rate import Rate
from app.models.operation import Operation
from app.models.template_links import TemplateOperation
from app.schemas.quote import QuoteCreate, QuoteOut, QuoteItemCreate, QuoteItemOut, QuoteUpdateCommercial, QuoteItemCommercialUpdate
from app.api.deps import get_current_user
from app.api.permissions import require_admin, require_sales, require_prod_or_better
from app.pricing.engine import calculate_item, price_item_with_policy

router = APIRouter()

def next_quote_number() -> str:
    import time
    return f"Q{int(time.time())}"

@router.post("/quotes", response_model=QuoteOut)
def create_quote(payload: QuoteCreate, db: Session = Depends(get_db), _=Depends(require_sales)):
    cust = db.query(Customer).filter(Customer.id == payload.customer_id).first()
    if not cust:
        raise HTTPException(status_code=404, detail="Customer not found")

    q = Quote(
        id=new_id(),
        quote_number=next_quote_number(),
        customer_id=payload.customer_id,
        contact_id=payload.contact_id,
        status="draft",
        pricing_version=settings.PRICING_VERSION,
        notes_internal=payload.notes_internal,
        subtotal_sell=0.0,
        vat=0.0,
        total_sell=0.0,
    )
    db.add(q); db.commit(); db.refresh(q)
    return q

@router.get("/quotes/{quote_id}", response_model=QuoteOut)
def get_quote(quote_id: str, db: Session = Depends(get_db), _=Depends(require_prod_or_better)):
    q = db.query(Quote).filter(Quote.id == quote_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Quote not found")
    return q

@router.put("/quotes/{quote_id}/commercial", response_model=QuoteOut)
def update_quote_commercial(quote_id: str, payload: QuoteUpdateCommercial, db: Session = Depends(get_db), _=Depends(require_sales)):
    q = db.query(Quote).filter(Quote.id == quote_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Quote not found")

    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(q, k, v)

    db.add(q); db.commit(); db.refresh(q)
    return q

@router.put("/quote-items/{item_id}/commercial", response_model=QuoteItemOut)
def update_item_commercial(item_id: str, payload: QuoteItemCommercialUpdate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    item = db.query(QuoteItem).filter(QuoteItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    q = db.query(Quote).filter(Quote.id == item.quote_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Quote not found")

    # If quote totals locked, don't allow changing item sells unless sales/admin rule later
    # For now, allow changes but force a recalc endpoint to apply.
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(item, k, v)

    db.add(item); db.commit(); db.refresh(item)
    return item

@router.post("/quotes/{quote_id}/recalc", response_model=QuoteOut)
def recalc_quote(quote_id: str, db: Session = Depends(get_db), _=Depends(require_sales)):
    q = db.query(Quote).filter(Quote.id == quote_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Quote not found")

    cust = db.query(Customer).filter(Customer.id == q.customer_id).first()
    if not cust:
        raise HTTPException(status_code=404, detail="Customer missing")

    items = db.query(QuoteItem).filter(QuoteItem.quote_id == q.id).all()
    if not items:
        q.subtotal_sell = 0.0
        q.vat = 0.0
        q.total_sell = 0.0
        db.add(q); db.commit(); db.refresh(q)
        return q

    # load rates once
    rates = db.query(Rate).all()
    rates_by_type = {
        r.rate_type: {"setup_minutes": r.setup_minutes, "hourly_cost_gbp": r.hourly_cost_gbp, "run_speed": r.run_speed}
        for r in rates
    }

    for item in items:
        t = db.query(ProductTemplate).filter(ProductTemplate.id == item.template_id).first()
        if not t:
            continue

        m = db.query(Material).filter(Material.id == t.default_material_id).first()
        if not m:
            continue

        # Build finish_blocks from DB (TemplateOperation + Operation) or fall back to template rules
        links = (
            db.query(TemplateOperation)
            .filter(TemplateOperation.template_id == t.id)
            .order_by(TemplateOperation.sort_order.asc())
            .all()
        )
        if links:
            ops_by_id = {}
            op_ids = [ln.operation_id for ln in links]
            ops = db.query(Operation).filter(Operation.id.in_(op_ids), Operation.active == True).all()
            ops_by_id = {o.id: o for o in ops}
            finish_blocks = []
            for ln in links:
                op = ops_by_id.get(ln.operation_id)
                if not op:
                    continue
                merged = dict(op.params or {})
                merged.update(ln.params_override or {})
                finish_blocks.append({
                    "code": op.code,
                    "calc_model": op.calc_model,
                    "rate_type": op.rate_type,
                    "params": merged,
                })
        else:
            finish_blocks = (t.rules or {}).get("finish_blocks") or []

        template_payload = {"category": t.category, "rules": dict(t.rules or {})}
        template_payload["rules"]["finish_blocks"] = finish_blocks

        # Recalc COSTS from engine using current item geometry
        calc = calculate_item(
            template=template_payload,
            material={
                "type": m.type,
                "waste_pct_default": m.waste_pct_default,
                "cost_per_sheet_gbp": m.cost_per_sheet_gbp,
                "sheet_width_mm": m.sheet_width_mm,
                "sheet_height_mm": m.sheet_height_mm,
                "cost_per_lm_gbp": m.cost_per_lm_gbp,
                "roll_width_mm": m.roll_width_mm,
                "min_billable_lm": m.min_billable_lm,
            },
            rates_by_type=rates_by_type,
            item_input={
                "template_id": item.template_id,
                "title": item.title,
                "qty": item.qty,
                "width_mm": item.width_mm,
                "height_mm": item.height_mm,
                "sides": item.sides,
                "options": item.options,
            },
        )

        item.cost_total = calc["cost_total"]

        sell_total, m_pct, snap = price_item_with_policy(
            db=db,
            quote=q,
            customer=cust,
            template=t,
            item=item,
            base_cost_total=item.cost_total,
            calc_snapshot=calc["snapshot"],
        )
        item.sell_total = sell_total
        item.margin_pct = m_pct
        item.calc_snapshot = snap
        db.add(item)

    db.commit()

    # update quote totals
    items2 = db.query(QuoteItem).filter(QuoteItem.quote_id == q.id).all()
    subtotal = sum(i.sell_total for i in items2)
    q.subtotal_sell = round(subtotal, 2)
    q.vat = round(q.subtotal_sell * 0.20, 2)
    q.total_sell = round(q.subtotal_sell + q.vat, 2)
    db.add(q); db.commit(); db.refresh(q)
    return q

@router.get("/quotes/{quote_id}/items", response_model=list[QuoteItemOut])
def list_items(quote_id: str, db: Session = Depends(get_db), _=Depends(require_prod_or_better)):
    return db.query(QuoteItem).filter(QuoteItem.quote_id == quote_id).all()

@router.post("/quotes/{quote_id}/items", response_model=QuoteItemOut)
def add_item(quote_id: str, payload: QuoteItemCreate, db: Session = Depends(get_db), _=Depends(require_sales)):
    q = db.query(Quote).filter(Quote.id == quote_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Quote not found")

    t = db.query(ProductTemplate).filter(ProductTemplate.id == payload.template_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")

    m = db.query(Material).filter(Material.id == t.default_material_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Default material missing for template")

    rates = db.query(Rate).all()
    rates_by_type = {
        r.rate_type: {"setup_minutes": r.setup_minutes, "hourly_cost_gbp": r.hourly_cost_gbp, "run_speed": r.run_speed}
        for r in rates
    }

    # Build finish_blocks from DB (TemplateOperation + Operation) or fall back to template rules
    template_ops = (
        db.query(TemplateOperation)
        .filter(TemplateOperation.template_id == t.id)
        .order_by(TemplateOperation.sort_order.asc())
        .all()
    )
    if template_ops:
        finish_blocks = []
        for to in template_ops:
            op = db.query(Operation).filter(Operation.id == to.operation_id).first()
            if op and op.active:
                params = dict(op.params or {})
                params.update(to.params_override or {})
                finish_blocks.append({
                    "code": op.code,
                    "calc_model": op.calc_model,
                    "rate_type": op.rate_type,
                    "params": params,
                })
    else:
        finish_blocks = (t.rules or {}).get("finish_blocks") or []

    template_payload = {"category": t.category, "rules": dict(t.rules or {})}
    template_payload["rules"]["finish_blocks"] = finish_blocks

    calc = calculate_item(
        template=template_payload,
        material={
            "type": m.type,
            "waste_pct_default": m.waste_pct_default,
            "cost_per_sheet_gbp": m.cost_per_sheet_gbp,
            "sheet_width_mm": m.sheet_width_mm,
            "sheet_height_mm": m.sheet_height_mm,
            "cost_per_lm_gbp": m.cost_per_lm_gbp,
            "roll_width_mm": m.roll_width_mm,
            "min_billable_lm": m.min_billable_lm,
        },
        rates_by_type=rates_by_type,
        item_input=payload.model_dump(),
    )

    cust = db.query(Customer).filter(Customer.id == q.customer_id).first()
    if not cust:
        raise HTTPException(status_code=404, detail="Customer missing")

    # create item first with cost and snapshot (sell will be set below)
    item = QuoteItem(
        id=new_id(),
        quote_id=q.id,
        template_id=t.id,
        title=payload.title,
        qty=payload.qty,
        width_mm=payload.width_mm,
        height_mm=payload.height_mm,
        sides=payload.sides,
        options=payload.options,
        cost_total=calc["cost_total"],
        sell_total=0.0,
        margin_pct=0.0,
        calc_snapshot=calc["snapshot"],
        sell_locked=False,
        manual_sell_total=None,
        manual_discount_pct=0.0,
        manual_reason="",
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    sell_total, m_pct, snap = price_item_with_policy(
        db=db,
        quote=q,
        customer=cust,
        template=t,
        item=item,
        base_cost_total=item.cost_total,
        calc_snapshot=item.calc_snapshot,
    )
    item.sell_total = sell_total
    item.margin_pct = m_pct
    item.calc_snapshot = snap
    db.add(item)
    db.commit()
    db.refresh(item)

    # Update quote totals
    items = db.query(QuoteItem).filter(QuoteItem.quote_id == q.id).all()
    subtotal = sum(i.sell_total for i in items)
    q.subtotal_sell = round(subtotal, 2)
    q.vat = round(q.subtotal_sell * 0.20, 2)
    q.total_sell = round(q.subtotal_sell + q.vat, 2)
    db.add(q); db.commit()

    return item
