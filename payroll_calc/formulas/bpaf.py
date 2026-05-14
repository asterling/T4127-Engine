"""Dynamic Basic Personal Amount formulas (BPAF, BPAMB, BPAYT).

From T4127 Chapter 2.
"""

from decimal import Decimal

from ..config import (
    BPAF_MAX, BPAF_MIN, BPAF_CLAWBACK_START, BPAF_CLAWBACK_END,
    BPAF_CLAWBACK_AMOUNT, BPAF_CLAWBACK_RANGE,
    BPAMB_MAX, BPAMB_CLAWBACK_START, BPAMB_CLAWBACK_END,
)
from ..rounding import round_tax

_BPAF_MAX = Decimal(BPAF_MAX)
_BPAF_MIN = Decimal(BPAF_MIN)
_BPAF_START = Decimal(BPAF_CLAWBACK_START)
_BPAF_END = Decimal(BPAF_CLAWBACK_END)
_BPAF_AMOUNT = Decimal(BPAF_CLAWBACK_AMOUNT)
_BPAF_RANGE = Decimal(BPAF_CLAWBACK_RANGE)

_BPAMB_MAX = Decimal(BPAMB_MAX)
_BPAMB_START = Decimal(BPAMB_CLAWBACK_START)
_BPAMB_END = Decimal(BPAMB_CLAWBACK_END)


def calc_bpaf(ni: Decimal) -> Decimal:
    """Calculate Federal Basic Personal Amount based on net income.

    NI = A + HD (annual taxable income + prescribed zone deduction)

    Where NI <= $181,440: BPAF = $16,452
    Where NI >= $258,482: BPAF = $14,829
    Otherwise: BPAF = $16,452 - (NI - $181,440) × ($1,623 / $77,042)
    """
    if ni <= _BPAF_START:
        return _BPAF_MAX
    if ni >= _BPAF_END:
        return _BPAF_MIN
    # Note: "no rounding on the division" per T4127
    result = _BPAF_MAX - (ni - _BPAF_START) * (_BPAF_AMOUNT / _BPAF_RANGE)
    return round_tax(result)


def calc_bpamb(ni: Decimal) -> Decimal:
    """Calculate Manitoba Basic Personal Amount based on net income.

    Where NI <= $200,000: BPAMB = $15,780
    Where NI >= $400,000: BPAMB = $0
    Otherwise: BPAMB = $15,780 - (NI - $200,000) × ($15,780 / $200,000)
    """
    if ni <= _BPAMB_START:
        return _BPAMB_MAX
    if ni >= _BPAMB_END:
        return Decimal(0)
    result = _BPAMB_MAX - (ni - _BPAMB_START) * (_BPAMB_MAX / (_BPAMB_END - _BPAMB_START))
    return round_tax(result)


def calc_bpayt(ni: Decimal) -> Decimal:
    """Calculate Yukon Basic Personal Amount. Mirrors BPAF."""
    return calc_bpaf(ni)
