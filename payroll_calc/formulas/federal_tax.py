"""Steps 2-3 — Basic federal tax (T3) and annual federal tax (T1)."""

from decimal import Decimal

from ..data.schema import TaxBracket

ZERO = Decimal(0)


def _find_bracket(A: Decimal, brackets: list[TaxBracket]) -> TaxBracket:
    """Find the applicable tax bracket for annual taxable income A."""
    applicable = brackets[0]
    for bracket in brackets:
        if A >= bracket.threshold:
            applicable = bracket
        else:
            break
    return applicable


def calc_t3(
    A: Decimal,
    brackets: list[TaxBracket],
    K1: Decimal,
    K2: Decimal,
    K3: Decimal = ZERO,
    K4: Decimal = ZERO,
) -> Decimal:
    """Calculate basic federal tax (T3).

    T3 = (R × A) - K - K1 - K2 - K3 - K4
    Floor at 0.
    """
    bracket = _find_bracket(A, brackets)
    T3 = bracket.rate * A - bracket.constant - K1 - K2 - K3 - K4
    return max(ZERO, T3)


def calc_t1(
    T3: Decimal,
    P: int = 1,
    LCF: Decimal = ZERO,
    is_quebec: bool = False,
    is_outside_canada: bool = False,
    abatement: Decimal = ZERO,
    surtax: Decimal = ZERO,
) -> Decimal:
    """Calculate annual federal tax (T1).

    Standard:         T1 = T3 - P × LCF
    Quebec:           T1 = (T3 - P × LCF) - abatement × T3
    Outside Canada:   T1 = T3 + surtax × T3 - P × LCF
    """
    p = Decimal(P)

    if is_quebec:
        result = (T3 - p * LCF)
        if result < ZERO:
            result = ZERO
        result = result - abatement * T3
    elif is_outside_canada:
        result = T3 + surtax * T3 - p * LCF
    else:
        result = T3 - p * LCF

    return max(ZERO, result)
