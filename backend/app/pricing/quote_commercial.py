from __future__ import annotations
from decimal import Decimal
from typing import Optional
from app.pricing.money import d, money
from app.pricing.sell_policy import apply_rounding, sell_from_margin, enforce_min_margin, margin_pct

def apply_line_controls(
    *,
    cost_total: Decimal,
    base_sell: Decimal,
    line_sell_locked: bool,
    manual_sell_total: Optional[float],
    manual_discount_pct: float,
    rounding: dict,
) -> tuple[Decimal, Decimal, dict]:
    meta = {}

    if line_sell_locked:
        if manual_sell_total is None:
            # locked but missing manual - fallback to base
            meta["warning"] = "sell_locked true but manual_sell_total missing; fallback to base_sell"
            sell = base_sell
        else:
            sell = money(d(manual_sell_total))
        sell = apply_rounding(sell, rounding)
        m = margin_pct(cost_total, sell)
        meta["line_override"] = {"sell_locked": True, "manual_sell_total": float(sell)}
        return sell, m, meta

    # line discount (applied to base)
    disc = d(manual_discount_pct or 0.0)
    if disc < 0:
        disc = d(0)
    if disc > d(0.95):
        disc = d(0.95)

    sell = base_sell * (d(1) - disc)
    sell = money(sell)
    sell = apply_rounding(sell, rounding)
    m = margin_pct(cost_total, sell)
    if disc > 0:
        meta["line_override"] = {"manual_discount_pct": float(disc), "sell_after_line_discount": float(sell)}
    return sell, m, meta

def apply_quote_discount(sell: Decimal, quote_discount_pct: float, rounding: dict) -> Decimal:
    disc = d(quote_discount_pct or 0.0)
    if disc < 0:
        disc = d(0)
    if disc > d(0.80):
        disc = d(0.80)
    out = money(sell * (d(1) - disc))
    return apply_rounding(out, rounding)
