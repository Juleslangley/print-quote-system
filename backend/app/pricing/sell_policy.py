"""
Sell-side policy: margin math, min margin enforcement, rounding.
"""
from __future__ import annotations
from decimal import Decimal, ROUND_HALF_UP, ROUND_UP
from app.pricing.money import d, money


def margin_pct(cost: Decimal, sell: Decimal) -> Decimal:
    """Margin percentage: (sell - cost) / sell. Returns 0 if sell <= 0."""
    if sell <= 0:
        return d(0)
    return (sell - cost) / sell


def sell_from_margin(cost: Decimal, target_margin_pct: Decimal) -> Decimal:
    """Sell price to achieve target margin: cost / (1 - target_margin_pct)."""
    if target_margin_pct >= d(1):
        return cost
    return money(cost / (d(1) - target_margin_pct))


def enforce_min_margin(cost: Decimal, sell: Decimal, min_margin_pct: Decimal) -> Decimal:
    """If margin on (cost, sell) is below min_margin_pct, return minimum sell that meets floor; else return sell."""
    if sell <= 0:
        return sell_from_margin(cost, min_margin_pct)
    if margin_pct(cost, sell) >= min_margin_pct:
        return sell
    return sell_from_margin(cost, min_margin_pct)


def apply_rounding(amount: Decimal, rounding: dict) -> Decimal:
    """
    Apply rounding policy to amount (GBP).
    rounding: {"mode": "NEAREST"|"UP"|"PSYCH_99"|"NONE", "step": number}
    """
    amount = d(amount)
    mode = (rounding.get("mode") or "NONE").upper()
    step = d(rounding.get("step", 0.01))

    if mode == "NONE":
        return money(amount)

    if mode == "NEAREST" and step > 0:
        # nearest step (e.g. 0.05 -> nearest 5p)
        q = (amount / step).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        return money(q * step)

    if mode == "UP" and step > 0:
        # round up to step (e.g. 1.00 -> whole pounds up)
        q = (amount / step).quantize(Decimal("1"), rounding=ROUND_UP)
        return money(q * step)

    if mode == "PSYCH_99":
        # round to *.99: e.g. 19.50 -> 19.99, 20.00 -> 20.99
        whole = int(amount.to_integral_value())
        if amount > whole:
            whole += 1
        return money(d(whole) - d("0.01"))

    return money(amount)
