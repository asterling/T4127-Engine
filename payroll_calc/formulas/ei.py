"""Chapter 7 — Employment Insurance premium formulas."""

from decimal import Decimal

from ..data.schema import EiParams
from ..rounding import round_tax

ZERO = Decimal(0)


def calc_ei_period(
    ie: Decimal,
    ei: EiParams,
    D1: Decimal = ZERO,
) -> Decimal:
    """Calculate EI premium for a pay period.

    Args:
        ie: Insurable earnings this period
        ei: EI parameters
        D1: Year-to-date EI premiums

    Returns:
        EI premium for this period
    """
    premium = min(
        max(ZERO, ei.max_employee_premium - D1),
        ei.employee_rate * ie,
    )
    return round_tax(premium)
