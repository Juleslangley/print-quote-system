from decimal import Decimal, ROUND_HALF_UP

def d(x) -> Decimal:
    return Decimal(str(x))

def money(x: Decimal) -> Decimal:
    return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
