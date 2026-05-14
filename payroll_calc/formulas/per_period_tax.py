"""Step 6 — Per-period tax deduction (T)."""

from decimal import Decimal

from ..rounding import round_tax

ZERO = Decimal(0)


def calc_per_period_tax(
    T1: Decimal,
    T2: Decimal,
    P: int,
    L: Decimal = ZERO,
) -> Decimal:
    """Calculate estimated tax deduction for the pay period.

    T = (T1 + T2) / P + L

    For Quebec/outside Canada employees: T = T1 / P + L (T2 = 0 already).
    """
    p = Decimal(P)
    T = (T1 + T2) / p + L
    return round_tax(T)
