from __future__ import annotations
from decimal import Decimal
from app.pricing.money import d, money

def perimeter_m(width_mm: Decimal, height_mm: Decimal) -> Decimal:
    return (d(2) * (width_mm + height_mm)) / d(1000)

def apply_operation(
    *,
    op_code: str,
    calc_model: str,
    rate_type: str,
    op_params: dict,
    rates_by_type: dict,
    width_mm: Decimal,
    height_mm: Decimal,
    print_sqm: Decimal,
    qty: int,
) -> dict:
    """
    Returns dict {code, minutes, cost, meta}
    """
    rate = rates_by_type.get(rate_type)
    if not rate:
        return {"code": op_code, "minutes": "0", "cost": 0.0, "meta": {"warning": f"Missing rate_type {rate_type}"}}

    setup_min = d(rate["setup_minutes"])
    hourly = d(rate["hourly_cost_gbp"])
    run_speed = rate.get("run_speed", {}) or {}
    per_m = perimeter_m(width_mm, height_mm)

    run_min = d(0)
    consumable = d(0)

    model = calc_model.upper()

    if model == "PERIM_M":
        m_per_min = d((run_speed.get("m_per_min", {}) or {}).get("straight", op_params.get("m_per_min", 6)))
        run_min = per_m / m_per_min

    elif model == "CONTOUR_PERIM_M":
        m_per_min = d((run_speed.get("m_per_min", {}) or {}).get("contour", op_params.get("m_per_min", 2)))
        run_min = per_m / m_per_min
        weed = op_params.get("weed_min_per_sqm")
        if weed is not None:
            run_min += d(weed) * print_sqm

    elif model == "ROUTER_PERIM_M":
        m_per_min = d(run_speed.get("router_m_per_min", op_params.get("router_m_per_min", 1.2)))
        run_min = per_m / m_per_min

    elif model == "SQM":
        # generic per sqm labour (use sqm_per_hour from run_speed)
        sqm_per_hr = d(run_speed.get("sqm_per_hour", op_params.get("sqm_per_hour", 30)))
        run_min = (print_sqm / sqm_per_hr) * d(60)

    elif model == "LAM_SQM":
        # lamination: consumable cost per sqm + labour at sqm/hr
        lam_cost_per_sqm = d(op_params.get("lam_cost_per_sqm", 1.10))
        consumable = lam_cost_per_sqm * print_sqm
        sqm_per_hr = d(run_speed.get("sqm_per_hour", op_params.get("sqm_per_hour", 30)))
        run_min = (print_sqm / sqm_per_hr) * d(60)

    elif model == "ITEM":
        minutes_per_item = d(op_params.get("minutes_per_item", 0.5))
        run_min = minutes_per_item * d(qty)

    elif model == "HEM_EYELET":
        hem_min_per_m = d(op_params.get("hem_min_per_m", 0.8))
        eyelet_min_each = d(op_params.get("eyelet_min_each", 0.25))
        spacing_mm = d(op_params.get("eyelet_spacing_mm", 300))

        eyelets = (per_m * d(1000) / spacing_mm).to_integral_value()
        if eyelets < 4:
            eyelets = d(4)

        run_min = (per_m * hem_min_per_m) + (eyelets * eyelet_min_each)

    else:
        return {"code": op_code, "minutes": "0", "cost": 0.0, "meta": {"warning": f"Unknown calc_model {calc_model}"}}

    total_min = setup_min + run_min
    labour = (total_min / d(60)) * hourly
    cost = money(labour + consumable)

    return {
        "code": op_code,
        "minutes": str(total_min),
        "cost": float(cost),
        "meta": {
            "calc_model": calc_model,
            "rate_type": rate_type,
            "perimeter_m": str(per_m),
            "consumable": str(consumable),
        },
    }


# Backward compatibility: map legacy finish_blocks (type/rate_type/params) to apply_operation
_LEGACY_TYPE_TO_CALC_MODEL = {
    "CUT_STRAIGHT": "PERIM_M",
    "CUT_CONTOUR": "CONTOUR_PERIM_M",
    "ROUTER_CUT": "ROUTER_PERIM_M",
    "LAMINATE_ROLL": "LAM_SQM",
    "PACK_STANDARD": "ITEM",
}

def finish_cost_block(block: dict, *, width_mm: Decimal, height_mm: Decimal, print_sqm: Decimal, qty: int, rates_by_type: dict) -> dict:
    """Legacy API: block = {type, rate_type, params}. Delegates to apply_operation and returns {name, minutes, cost, meta}."""
    btype = block.get("type", "")
    rate_type = block.get("rate_type")
    params = block.get("params", {}) or {}
    calc_model = _LEGACY_TYPE_TO_CALC_MODEL.get(btype)
    if not calc_model:
        return {"name": btype, "minutes": "0", "cost": 0.0, "meta": {"warning": f"Unknown finish type {btype}"}}
    res = apply_operation(
        op_code=btype,
        calc_model=calc_model,
        rate_type=rate_type or "",
        op_params=params,
        rates_by_type=rates_by_type,
        width_mm=width_mm,
        height_mm=height_mm,
        print_sqm=print_sqm,
        qty=qty,
    )
    return {"name": res["code"], "minutes": res["minutes"], "cost": res["cost"], "meta": res["meta"]}
