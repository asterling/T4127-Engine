"""Step 1 — Calculate annual taxable income (A)."""

from decimal import Decimal

ZERO = Decimal(0)


def calc_annual_taxable_income(
    P: int,
    I: Decimal,
    F: Decimal = ZERO,
    F2: Decimal = ZERO,
    F5A: Decimal = ZERO,
    U1: Decimal = ZERO,
    HD: Decimal = ZERO,
    F1: Decimal = ZERO,
) -> Decimal:
    """Calculate annual taxable income (A) per T4127 Step 1.

    A = P × (I - F - F2 - F5A - U1) - HD - F1

    Args:
        P: Number of pay periods in the year
        I: Gross remuneration for the pay period
        F: RPP/RRSP/PRPP contributions for the period
        F2: Alimony/maintenance deductions
        F5A: Additional CPP contributions (periodic portion)
        U1: Union dues for the period
        HD: Annual prescribed zone deduction
        F1: Annual deductions (child care, support payments)

    Returns:
        A (annual taxable income). If negative, caller should set T = L.
    """
    p = Decimal(P)
    return p * (I - F - F2 - F5A - U1) - HD - F1
