"""Province-specific tax adjustments (V1, V2, S, K5P, LCP).

From T4127 Step 5.
"""

from decimal import Decimal

from ..data.schema import JurisdictionParams

ZERO = Decimal(0)


# ── Ontario ────────────────────────────────────────────────────────────

def ontario_v1(T4: Decimal, params: JurisdictionParams) -> Decimal:
    """Ontario surtax.

    V1 tiers (from Table 8.2):
      20% of (T4 - $5,818) where T4 > $5,818
      36% of (T4 - $7,446) where T4 > $7,446
    """
    v1 = ZERO
    for tier in params.v1_tiers:
        if T4 > tier.threshold:
            v1 += tier.rate * (T4 - tier.threshold)
    return v1


def ontario_v2(A: Decimal) -> Decimal:
    """Ontario Health Premium (OHP).

    6-tier graduated schedule based on annual taxable income.
    """
    if A <= Decimal("20000"):
        return ZERO
    if A <= Decimal("36000"):
        return min(Decimal("300"), Decimal("0.06") * (A - Decimal("20000")))
    if A <= Decimal("48000"):
        return min(Decimal("450"), Decimal("300") + Decimal("0.06") * (A - Decimal("36000")))
    if A <= Decimal("72000"):
        return min(Decimal("600"), Decimal("450") + Decimal("0.25") * (A - Decimal("48000")))
    if A <= Decimal("200000"):
        return min(Decimal("750"), Decimal("600") + Decimal("0.25") * (A - Decimal("72000")))
    return min(Decimal("900"), Decimal("750") + Decimal("0.25") * (A - Decimal("200000")))


def ontario_s(T4: Decimal, V1: Decimal, S2: Decimal, Y: Decimal = ZERO) -> Decimal:
    """Ontario tax reduction.

    S = min(T4 + V1, 2 × (S2 + Y) - (T4 + V1))
    If negative, S = 0.

    Note: OHP (V2) is NOT reduced by S.
    """
    combined = T4 + V1
    reduction = Decimal(2) * (S2 + Y) - combined
    return max(ZERO, min(combined, reduction))


# ── British Columbia ──────────────────────────────────────────────────

def bc_s(A: Decimal, T4: Decimal, S2: Decimal) -> Decimal:
    """BC tax reduction.

    Where A <= $25,570: S = min(T4, S2)
    Where $25,570 < A <= $41,722: S = min(T4, S2 - (A - $25,570) × 3.56%)
    Where A > $41,722: S = 0
    """
    low = Decimal("25570")
    high = Decimal("41722")
    rate = Decimal("0.0356")

    if A <= low:
        return min(T4, S2)
    if A <= high:
        return min(T4, max(ZERO, S2 - (A - low) * rate))
    return ZERO


# ── Alberta ───────────────────────────────────────────────────────────

def alberta_k5p(K1P: Decimal, K2P: Decimal) -> Decimal:
    """Alberta supplemental non-refundable tax credit.

    K5P = max(0, (K1P + K2P - $4,896) × 0.25)
    """
    return max(ZERO, (K1P + K2P - Decimal("4896")) * Decimal("0.25"))
