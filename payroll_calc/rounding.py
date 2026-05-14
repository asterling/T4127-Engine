"""CRA-specific rounding utilities.

CRA rules (T4127 Chapter 1):
- Tax deductions: if 3rd decimal digit >= 5, round up 2nd digit; else truncate
- CPP contributions: same as tax
- EI premiums: same as tax
- CPP basic exemption per period: truncate at 2 decimal places (drop 3rd digit)
- Rate ratios: do not round
"""

from decimal import Decimal, ROUND_HALF_UP, ROUND_DOWN

TWO_PLACES = Decimal("0.01")


def round_tax(value: Decimal) -> Decimal:
    """Round to nearest cent per CRA rules (round half up)."""
    return value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def truncate_2dp(value: Decimal) -> Decimal:
    """Truncate to 2 decimal places (drop 3rd digit regardless of value).

    Used for CPP basic exemption per period.
    """
    return value.quantize(TWO_PLACES, rounding=ROUND_DOWN)
