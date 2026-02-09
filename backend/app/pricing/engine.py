from __future__ import annotations
from decimal import Decimal
from sqlalchemy.orm import Session
from app.models.quote import Quote, QuoteItem
from app.models.customer import Customer
from app.models.template import ProductTemplate
from app.models.pricing_rules import TemplatePricingRule
from app.pricing.money import d, money
from app.pricing.operations import apply_operation
from app.pricing.sell_policy import sell_from_margin, enforce_min_margin, apply_rounding, margin_pct
from app.pricing.quote_commercial import apply_line_controls, apply_quote_discount
from app.pricing.resolve import resolve_customer_pricing_rule, resolve_margin_profile_for_quote

# Legacy template rules use {"type": "CUT_STRAIGHT", "rate_type": "...", "params": {...}}
_LEGACY_TYPE_TO_CALC_MODEL = {
    "CUT_STRAIGHT": "PERIM_M",
    "CUT_CONTOUR": "CONTOUR_PERIM_M",
    "ROUTER_CUT": "ROUTER_PERIM_M",
    "LAMINATE_ROLL": "LAM_SQM",
    "PACK_STANDARD": "ITEM",
}

def _normalize_finish_block(block: dict) -> dict:
    if "code" in block and "calc_model" in block:
        return block
    if "type" in block:
        return {
            "code": block["type"],
            "calc_model": _LEGACY_TYPE_TO_CALC_MODEL.get(block["type"], "ITEM"),
            "rate_type": block.get("rate_type", ""),
            "params": block.get("params", {}) or {},
        }
    return block

def sqm(width_mm: Decimal, height_mm: Decimal) -> Decimal:
    return (width_mm * height_mm) / d(1_000_000)

def ceil_div(a: int, b: int) -> int:
    return (a + b - 1) // b

def calculate_item(*, template: dict, material: dict, rates_by_type: dict, item_input: dict) -> dict:
    qty = int(item_input["qty"])
    width_mm = d(item_input["width_mm"])
    height_mm = d(item_input["height_mm"])
    sides = int(item_input.get("sides", 1))
    options = item_input.get("options", {}) or {}

    rules = template.get("rules", {}) or {}
    category = template["category"]

    bleed_mm = d(rules.get("bleed_mm", 3))
    width_b = width_mm + bleed_mm * d(2)
    height_b = height_mm + bleed_mm * d(2)

    coverage = (options.get("coverage_class") or rules.get("coverage_class") or "medium").lower()
    ink_map = rules.get("ink_allowance_per_sqm_gbp", {"light": 0.60, "medium": 0.90, "heavy": 1.20})
    ink_allow = d(ink_map.get(coverage, ink_map.get("medium", 0.90)))

    waste_pct = d(options.get("waste_pct") if "waste_pct" in options else rules.get("waste_pct", material.get("waste_pct_default", 0.05)))
    print_mode = options.get("print_mode") or rules.get("print_mode") or "standard"
    white = bool(options.get("white", False))

    finish_blocks = rules.get("finish_blocks", []) or []
    snapshot: dict = {
        "inputs": {"qty": qty, "width_mm": str(width_mm), "height_mm": str(height_mm), "sides": sides, "bleed_mm": str(bleed_mm)},
        "category": category,
        "coverage_class": coverage,
        "print_mode": print_mode,
        "white": white,
    }

    material_cost = d(0)
    ink_cost = d(0)
    print_labour = d(0)

    if category == "rigid":
        sheet_w = d(material["sheet_width_mm"])
        sheet_h = d(material["sheet_height_mm"])
        cost_per_sheet = d(material["cost_per_sheet_gbp"])

        gutter = d(rules.get("gutter_mm", 10))
        fit_x = int((sheet_w + gutter) // (width_b + gutter))
        fit_y = int((sheet_h + gutter) // (height_b + gutter))
        items_per_sheet = fit_x * fit_y
        if items_per_sheet <= 0:
            raise ValueError("Item too large for selected sheet")

        base_sheets = ceil_div(qty, items_per_sheet)
        setup_waste_sheets = int(rules.get("setup_waste_sheets", 1))
        waste_sheets = setup_waste_sheets + int((d(base_sheets) * waste_pct).to_integral_value())
        total_sheets = base_sheets + waste_sheets

        material_cost = money(d(total_sheets) * cost_per_sheet)

        print_sqm = sqm(width_b, height_b) * d(qty) * d(sides)
        ink_cost = money(print_sqm * ink_allow)

        rate = rates_by_type.get("print_flatbed")
        if not rate:
            raise ValueError("Missing rate print_flatbed")

        setup_min = d(rate["setup_minutes"])
        hourly = d(rate["hourly_cost_gbp"])
        sqm_per_hr = d((rate.get("run_speed", {}).get("sqm_per_hour", {}) or {}).get(print_mode, 35))
        white_mult = d((rate.get("run_speed", {}) or {}).get("white_multiplier", 1.35))

        if white:
            ink_cost = money(d(ink_cost) * white_mult)

        run_hours = print_sqm / sqm_per_hr
        print_labour = money((setup_min / d(60)) * hourly + run_hours * hourly)

        snapshot["rigid"] = {
            "sheet_w_mm": str(sheet_w),
            "sheet_h_mm": str(sheet_h),
            "items_per_sheet": items_per_sheet,
            "base_sheets": base_sheets,
            "waste_sheets": waste_sheets,
            "total_sheets": total_sheets,
            "print_sqm": str(print_sqm),
        }

    elif category == "roll":
        roll_w = d(material["roll_width_mm"])
        cost_per_lm = d(material["cost_per_lm_gbp"])
        min_bill = d(material.get("min_billable_lm") or 0)

        setup_waste_lm = d(rules.get("setup_waste_lm", 1.0))

        fits_a = width_b <= roll_w
        lm_a = (height_b / d(1000)) * d(qty)
        fits_b = height_b <= roll_w
        lm_b = (width_b / d(1000)) * d(qty)

        if not (fits_a or fits_b):
            raise ValueError("Item too large for selected roll width")

        if fits_a and (not fits_b or lm_a <= lm_b):
            chosen = "A"
            lm_total = lm_a
        else:
            chosen = "B"
            lm_total = lm_b

        lm_total = lm_total + setup_waste_lm
        lm_total = lm_total * (d(1) + waste_pct)

        if lm_total < min_bill:
            lm_total = min_bill

        material_cost = money(lm_total * cost_per_lm)

        print_sqm = sqm(width_b, height_b) * d(qty) * d(sides)
        ink_cost = money(print_sqm * ink_allow)

        rate = rates_by_type.get("print_roll")
        if not rate:
            raise ValueError("Missing rate print_roll")

        setup_min = d(rate["setup_minutes"])
        hourly = d(rate["hourly_cost_gbp"])
        sqm_per_hr = d((rate.get("run_speed", {}).get("sqm_per_hour", {}) or {}).get(print_mode, 25))

        run_hours = print_sqm / sqm_per_hr
        print_labour = money((setup_min / d(60)) * hourly + run_hours * hourly)

        snapshot["roll"] = {
            "roll_width_mm": str(roll_w),
            "orientation": chosen,
            "lm_total": str(lm_total),
            "print_sqm": str(print_sqm),
        }
    else:
        raise ValueError(f"Unknown category {category}")

    # finishing
    finish_costs = []
    finish_total = d(0)
    print_sqm_val = d(snapshot[category]["print_sqm"])

    # NOTE: in the new approach, `finish_blocks` will be passed in from DB as a list of operations.
    # Each block dict: {"code":"CUT_STRAIGHT","calc_model":"PERIM_M","rate_type":"cut_knife","params":{...}}
    # Legacy rules may use {"type":"CUT_STRAIGHT","rate_type":"cut_knife","params":{...}} (normalized below).
    for block in finish_blocks:
        b = _normalize_finish_block(block)
        res = apply_operation(
            op_code=b["code"],
            calc_model=b["calc_model"],
            rate_type=b["rate_type"],
            op_params=b.get("params", {}) or {},
            rates_by_type=rates_by_type,
            width_mm=width_b,
            height_mm=height_b,
            print_sqm=print_sqm_val,
            qty=qty,
        )
        finish_costs.append(res)
        finish_total += d(res["cost"])

    cost_total = money(d(material_cost) + d(ink_cost) + d(print_labour) + money(finish_total))

    # v1 selling rule: target margin fixed per template (default 40%)
    target_margin = d(rules.get("target_margin_pct", 0.40))
    sell_total = money(cost_total / (d(1) - target_margin))
    margin_pct = d(0) if sell_total == 0 else (sell_total - cost_total) / sell_total

    snapshot["costs"] = {
        "material_cost": float(material_cost),
        "ink_cost": float(ink_cost),
        "print_labour_cost": float(print_labour),
        "finish_costs": finish_costs,
        "finish_total": float(money(finish_total)),
        "cost_total": float(cost_total),
        "target_margin_pct": float(target_margin),
        "sell_total": float(sell_total),
        "margin_pct": float(margin_pct),
    }

    return {"cost_total": float(cost_total), "sell_total": float(sell_total), "margin_pct": float(margin_pct), "snapshot": snapshot}


def price_item_with_policy(
    *,
    db: Session,
    quote: Quote,
    customer: Customer,
    template: ProductTemplate,
    item: QuoteItem,
    base_cost_total: float,
    calc_snapshot: dict,
):
    t_rule = db.query(TemplatePricingRule).filter(TemplatePricingRule.template_id == template.id, TemplatePricingRule.active == True).first()
    c_rule = resolve_customer_pricing_rule(db, quote.customer_id, template.category, template.id)
    policy = resolve_margin_profile_for_quote(db, quote=quote, customer=customer, template=template, t_rule=t_rule, c_rule=c_rule)

    cost_total = d(base_cost_total)

    # base sell from target margin
    sell = sell_from_margin(cost_total, policy["target_margin"])

    # enforce per-line min sell
    if sell < policy["min_sell"]:
        sell = policy["min_sell"]

    # apply multipliers
    sell = money(sell * policy["sell_multiplier"])

    # enforce min margin
    sell = enforce_min_margin(cost_total, sell, policy["min_margin"])

    # rounding
    sell = apply_rounding(sell, policy["rounding"])

    # line level overrides
    sell, m_pct, line_meta = apply_line_controls(
        cost_total=cost_total,
        base_sell=sell,
        line_sell_locked=bool(item.sell_locked),
        manual_sell_total=item.manual_sell_total,
        manual_discount_pct=item.manual_discount_pct,
        rounding=policy["rounding"],
    )

    # quote-level discount applied last (v1)
    sell_after_quote_disc = apply_quote_discount(sell, quote.discount_pct, policy["rounding"])
    m_pct_final = margin_pct(cost_total, sell_after_quote_disc)

    snap = calc_snapshot or {}
    snap.setdefault("commercial_policy", {})
    snap["commercial_policy"].update({
        "profile_id": policy["profile_id"],
        "profile_name": policy["profile_name"],
        "target_margin_pct": float(policy["target_margin"]),
        "min_margin_pct": float(policy["min_margin"]),
        "min_sell_gbp": float(policy["min_sell"]),
        "sell_multiplier": float(policy["sell_multiplier"]),
        "rounding": policy["rounding"],
        "quote_discount_pct": float(quote.discount_pct or 0.0),
        "sell_before_quote_discount": float(sell),
        "sell_final": float(sell_after_quote_disc),
        "margin_pct_final": float(m_pct_final),
        **line_meta
    })

    return float(sell_after_quote_disc), float(m_pct_final), snap
