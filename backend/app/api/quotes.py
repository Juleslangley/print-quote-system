import copy
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.core.config import settings
from app.models.base import new_id
from app.models.quote import Quote, QuoteItem
from app.models.quote_part import QuotePart
from app.models.quote_price_snapshot import QuotePriceSnapshot
from app.models.customer import Customer
from app.models.template import ProductTemplate
from app.models.material import Material
from app.models.material_size import MaterialSize
from app.models.machine import Machine
from app.models.job import Job
from app.models.rate import Rate
from app.models.operation import Operation
from app.models.template_links import TemplateOperation
from app.schemas.quote import (
    QuoteCreate,
    QuoteOut,
    QuotePatch,
    QuoteItemCreate,
    QuoteItemOut,
    QuoteUpdateCommercial,
    QuoteItemCommercialUpdate,
)
from app.api.deps import get_current_user
from app.api.permissions import require_admin, require_sales, require_prod_or_better
from app.pricing.engine import calculate_item, price_item_with_policy
from app.services.job_routing import (
    JobType,
    apply_defaults_to_item_options,
    get_jobtype_defaults,
    normalize_job_type,
)
from app.services.mis_pricing import price_quote

router = APIRouter()


def _resolve_quote_job_type(db: Session, q: Quote) -> str:
    # Discovery note: Quote already links to Job via quote.job_id, so routing is derived from Job.
    if q.job_id:
        job = db.query(Job).filter(Job.id == q.job_id).first()
        if job and getattr(job, "job_type", None):
            return normalize_job_type(job.job_type)
    return JobType.LARGE_FORMAT_SHEET


def _apply_setup_minutes_override(item_rates: dict, options: dict) -> None:
    setup_minutes = options.get("setup_minutes")
    if setup_minutes is None:
        return
    try:
        setup_minutes_val = float(setup_minutes)
    except (TypeError, ValueError):
        return
    for rate_type in ("print_flatbed", "print_roll"):
        if rate_type in item_rates:
            item_rates[rate_type]["setup_minutes"] = setup_minutes_val


def _material_for_pricing(m: Material, db: Session) -> dict:
    """Build material dict for pricing. For roll materials with sizes, use first roll width."""
    base = {
        "type": m.type,
        "waste_pct_default": m.waste_pct_default,
        "cost_per_sheet_gbp": m.cost_per_sheet_gbp,
        "sheet_width_mm": m.sheet_width_mm,
        "sheet_height_mm": m.sheet_height_mm,
        "cost_per_lm_gbp": m.cost_per_lm_gbp,
        "roll_width_mm": m.roll_width_mm,
        "min_billable_lm": m.min_billable_lm,
    }
    if m.type == "roll":
        first_size = (
            db.query(MaterialSize)
            .filter(
                MaterialSize.material_id == m.id,
                MaterialSize.active == True,
                MaterialSize.cost_per_lm_gbp.is_not(None),
            )
            .order_by(MaterialSize.sort_order.asc(), MaterialSize.width_mm.asc())
            .first()
        )
        if first_size:
            base["roll_width_mm"] = first_size.width_mm
            base["cost_per_lm_gbp"] = first_size.cost_per_lm_gbp
    return base


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
        name=payload.name or "",
        default_job_type=payload.default_job_type,
    )
    db.add(q)
    db.commit()
    db.refresh(q)
    return q

@router.get("/quotes/{quote_id}", response_model=QuoteOut)
def get_quote(quote_id: str, db: Session = Depends(get_db), _=Depends(require_prod_or_better)):
    q = db.query(Quote).filter(Quote.id == quote_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Quote not found")
    return q

def _auto_unlock_if_priced(db: Session, quote_id: str) -> None:
    """If quote status is priced, set to draft. Snapshots are never deleted."""
    q = db.query(Quote).filter(Quote.id == quote_id).first()
    if q and q.status and str(q.status).lower() == "priced":
        q.status = "draft"
        db.add(q)


@router.patch("/quotes/{quote_id}", response_model=QuoteOut)
def patch_quote(
    quote_id: str,
    payload: QuotePatch,
    db: Session = Depends(get_db),
    _=Depends(require_sales),
):
    """PATCH quote. AUTO-UNLOCK: if PRICED and any change, set status to DRAFT."""
    q = db.query(Quote).filter(Quote.id == quote_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Quote not found")
    _auto_unlock_if_priced(db, quote_id)
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(q, k, v)
    db.add(q)
    db.commit()
    db.refresh(q)
    return q


@router.put("/quotes/{quote_id}/commercial", response_model=QuoteOut)
def update_quote_commercial(quote_id: str, payload: QuoteUpdateCommercial, db: Session = Depends(get_db), _=Depends(require_sales)):
    q = db.query(Quote).filter(Quote.id == quote_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Quote not found")
    _auto_unlock_if_priced(db, quote_id)
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(q, k, v)
    db.add(q)
    db.commit()
    db.refresh(q)
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
        r.rate_type: {"setup_minutes": r.setup_minutes, "hourly_cost_gbp": r.hourly_cost_gbp, "run_speed": r.run_speed or {}}
        for r in rates
    }
    job_type = _resolve_quote_job_type(db, q)
    routing_defaults = get_jobtype_defaults(job_type)
    job_type = _resolve_quote_job_type(db, q)
    routing_defaults = get_jobtype_defaults(job_type)

    # Cutter machine for tool speeds (used per material)
    cutter_machine = (
        db.query(Machine)
        .filter(Machine.category == "cutter", Machine.active == True)
        .order_by(Machine.sort_order.asc(), Machine.name.asc())
        .first()
    )
    cutter_tools = (cutter_machine.meta or {}).get("tools", []) if cutter_machine else []

    for item in items:
        t = db.query(ProductTemplate).filter(ProductTemplate.id == item.template_id).first()
        if not t:
            continue

        m = db.query(Material).filter(Material.id == t.default_material_id).first()
        if not m:
            continue

        # Per-item rates: override cutter run_speed from material's selected tool
        item_rates = copy.deepcopy(rates_by_type)
        tool_key = (m.meta or {}).get("cutter_tool_key")
        if tool_key and cutter_tools:
            selected = next((tool for tool in cutter_tools if isinstance(tool, dict) and tool.get("key") == tool_key), None)
            if selected and isinstance(selected, dict):
                speed = selected.get("speed_m_per_min")
                if speed is not None:
                    run_speed_override = {
                        "m_per_min": {"straight": speed, "contour": speed},
                        "router_m_per_min": speed,
                    }
                    for rtype in ("cut_knife", "cut_router"):
                        if rtype in item_rates:
                            item_rates[rtype]["run_speed"] = run_speed_override

        # Keep existing explicit options, only fill missing defaults from job routing.
        options_for_calc = apply_defaults_to_item_options(item.options or {}, job_type)
        _apply_setup_minutes_override(item_rates, options_for_calc)

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

        # Build material dict: for roll, use first size if material has roll widths
        material_dict = _material_for_pricing(m, db)

        # Recalc COSTS from engine using current item geometry
        calc = calculate_item(
            template=template_payload,
            material=material_dict,
            rates_by_type=item_rates,
            item_input={
                "template_id": item.template_id,
                "title": item.title,
                "qty": item.qty,
                "width_mm": item.width_mm,
                "height_mm": item.height_mm,
                "sides": item.sides,
                "options": options_for_calc,
            },
        )
        calc.setdefault("snapshot", {}).setdefault("routing", {})
        calc["snapshot"]["routing"].update(
            {
                "job_type": job_type,
                "lane_effective": routing_defaults["lane"],
                "material_mode": routing_defaults["material_mode"],
                "machine_key_effective": routing_defaults["default_machine_key"],
                "effective_waste_pct": options_for_calc.get("waste_pct"),
                "effective_setup_minutes": options_for_calc.get("setup_minutes"),
                "material_mode_matches_selected_material": (
                    (routing_defaults["material_mode"] == "ROLL" and m.type == "roll")
                    or (routing_defaults["material_mode"] == "SHEET" and m.type == "sheet")
                ),
            }
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
        r.rate_type: {"setup_minutes": r.setup_minutes, "hourly_cost_gbp": r.hourly_cost_gbp, "run_speed": r.run_speed or {}}
        for r in rates
    }

    # Override cutter run_speed from material's selected tool
    cutter_machine = (
        db.query(Machine)
        .filter(Machine.category == "cutter", Machine.active == True)
        .order_by(Machine.sort_order.asc(), Machine.name.asc())
        .first()
    )
    cutter_tools = (cutter_machine.meta or {}).get("tools", []) if cutter_machine else []
    item_rates = copy.deepcopy(rates_by_type)
    tool_key = (m.meta or {}).get("cutter_tool_key")
    if tool_key and cutter_tools:
        selected = next((tool for tool in cutter_tools if isinstance(tool, dict) and tool.get("key") == tool_key), None)
        if selected and isinstance(selected, dict):
            speed = selected.get("speed_m_per_min")
            if speed is not None:
                run_speed_override = {
                    "m_per_min": {"straight": speed, "contour": speed},
                    "router_m_per_min": speed,
                }
                for rtype in ("cut_knife", "cut_router"):
                    if rtype in item_rates:
                        item_rates[rtype]["run_speed"] = run_speed_override

    job_type = _resolve_quote_job_type(db, q)
    routing_defaults = get_jobtype_defaults(job_type)
    payload_data = payload.model_dump()
    payload_data["options"] = apply_defaults_to_item_options(payload_data.get("options") or {}, job_type)
    _apply_setup_minutes_override(item_rates, payload_data["options"])

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

    material_dict = _material_for_pricing(m, db)
    calc = calculate_item(
        template=template_payload,
        material=material_dict,
        rates_by_type=item_rates,
        item_input=payload_data,
    )
    calc.setdefault("snapshot", {}).setdefault("routing", {})
    calc["snapshot"]["routing"].update(
        {
            "job_type": job_type,
            "lane_effective": routing_defaults["lane"],
            "material_mode": routing_defaults["material_mode"],
            "machine_key_effective": routing_defaults["default_machine_key"],
            "effective_waste_pct": payload_data["options"].get("waste_pct"),
            "effective_setup_minutes": payload_data["options"].get("setup_minutes"),
            "material_mode_matches_selected_material": (
                (routing_defaults["material_mode"] == "ROLL" and m.type == "roll")
                or (routing_defaults["material_mode"] == "SHEET" and m.type == "sheet")
            ),
        }
    )

    cust = db.query(Customer).filter(Customer.id == q.customer_id).first()
    if not cust:
        raise HTTPException(status_code=404, detail="Customer missing")

    # create item first with cost and snapshot (sell will be set below)
    item = QuoteItem(
        id=new_id(),
        quote_id=q.id,
        template_id=t.id,
        title=payload_data["title"],
        qty=payload_data["qty"],
        width_mm=payload_data["width_mm"],
        height_mm=payload_data["height_mm"],
        sides=payload_data.get("sides", 1),
        options=payload_data.get("options", {}),
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


# --- MIS-style pricing & lock ---

@router.get("/quotes/{quote_id}/latest-snapshot")
def get_latest_snapshot(quote_id: str, db: Session = Depends(get_db), _=Depends(require_sales)):
    """Return latest QuotePriceSnapshot for display (revision, timestamp, input_hash)."""
    latest = (
        db.query(QuotePriceSnapshot)
        .filter(QuotePriceSnapshot.quote_id == quote_id)
        .order_by(QuotePriceSnapshot.revision.desc())
        .first()
    )
    if not latest:
        return None
    return {
        "id": latest.id,
        "revision": latest.revision,
        "pricing_version": latest.pricing_version,
        "input_hash": latest.input_hash,
        "created_at": latest.created_at.isoformat() if hasattr(latest.created_at, "isoformat") else str(latest.created_at),
    }


@router.post("/quotes/{quote_id}/price")
def post_quote_price(quote_id: str, db: Session = Depends(get_db), _=Depends(require_sales)):
    """Price whole quote. Does NOT persist. Returns full QuotePriceResult."""
    return price_quote(db, quote_id)


@router.post("/quotes/{quote_id}/lock-price")
def lock_quote_price(quote_id: str, db: Session = Depends(get_db), _=Depends(require_sales)):
    """Lock price. INPUT_HASH no-op: if current hash matches latest snapshot, do NOT create new revision."""
    q = db.query(Quote).filter(Quote.id == quote_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Quote not found")
    parts = db.query(QuotePart).filter(QuotePart.quote_id == quote_id).all()
    result = price_quote(db, quote_id)
    input_hash = result["input_hash"]

    latest = (
        db.query(QuotePriceSnapshot)
        .filter(QuotePriceSnapshot.quote_id == quote_id)
        .order_by(QuotePriceSnapshot.revision.desc())
        .first()
    )

    if latest and latest.input_hash == input_hash:
        return {
            "created": False,
            "snapshot": {
                "id": latest.id,
                "revision": latest.revision,
                "pricing_version": latest.pricing_version,
                "input_hash": latest.input_hash,
                "created_at": latest.created_at.isoformat() if hasattr(latest.created_at, "isoformat") else str(latest.created_at),
            },
            "result": latest.result_json,
        }

    revision = (latest.revision + 1) if latest else 1
    snap = QuotePriceSnapshot(
        id=new_id(),
        quote_id=quote_id,
        revision=revision,
        pricing_version=result["pricing_version"],
        input_hash=input_hash,
        result_json=result,
    )
    db.add(snap)
    q.status = "priced"
    db.add(q)
    db.commit()
    db.refresh(snap)
    return {
        "created": True,
        "snapshot": {
            "id": snap.id,
            "revision": snap.revision,
            "pricing_version": snap.pricing_version,
            "input_hash": snap.input_hash,
            "created_at": snap.created_at.isoformat() if hasattr(snap.created_at, "isoformat") else str(snap.created_at),
        },
        "result": result,
    }
