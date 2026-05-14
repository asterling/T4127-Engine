"""Tax on bonuses and non-periodic payments (TB formula).

From T4127 Step 3, "Tax calculation formulas for bonuses".
"""

from decimal import Decimal

ZERO = Decimal(0)


def calc_bonus_tax(
    t1_t2_with_bonus: Decimal,
    t1_t2_without_bonus: Decimal,
) -> Decimal:
    """Calculate tax on a bonus/non-periodic payment.

    TB = (T1 + T2 with bonus) - (T1 + T2 without bonus)

    The caller is responsible for computing the two annual tax amounts
    by running the full calculation twice (with and without the bonus
    added to A).
    """
    TB = t1_t2_with_bonus - t1_t2_without_bonus
    return max(ZERO, TB)
