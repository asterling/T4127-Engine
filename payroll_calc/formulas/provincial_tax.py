"""Steps 4-5 — Provincial/territorial tax (T4, T2)."""

from decimal import Decimal

from ..config import Province
from ..data.schema import TaxBracket, JurisdictionParams
from . import province_specific as ps

ZERO = Decimal(0)


def _find_bracket(A: Decimal, brackets: list[TaxBracket]) -> TaxBracket:
    """Find the applicable provincial tax bracket for annual taxable income A."""
    applicable = brackets[0]
    for bracket in brackets:
        if A >= bracket.threshold:
            applicable = bracket
        else:
            break
    return applicable


def calc_t4(
    A: Decimal,
    brackets: list[TaxBracket],
    K1P: Decimal,
    K2P: Decimal,
    K3P: Decimal = ZERO,
    K4P: Decimal = ZERO,
    K5P: Decimal = ZERO,
) -> Decimal:
    """Calculate basic provincial tax (T4).

    T4 = (V × A) - KP - K1P - K2P - K3P - K4P - K5P
    Floor at 0.
    """
    bracket = _find_bracket(A, brackets)
    T4 = bracket.rate * A - bracket.constant - K1P - K2P - K3P - K4P - K5P
    return max(ZERO, T4)


def calc_t2(
    A: Decimal,
    T4: Decimal,
    province: Province,
    params: JurisdictionParams,
    P: int = 1,
    LCP: Decimal = ZERO,
    Y: Decimal = ZERO,
) -> Decimal:
    """Calculate annual provincial tax (T2).

    T2 = T4 + V1 + V2 - S - P × LCP
    Floor at 0.

    Province-specific components:
      - Ontario: V1 (surtax), V2 (OHP), S (tax reduction)
      - BC: S (tax reduction)
      - Others: V1=V2=S=0
    """
    V1 = ZERO
    V2 = ZERO
    S = ZERO
    p = Decimal(P)

    if province == Province.ON:
        V1 = ps.ontario_v1(T4, params)
        V2 = ps.ontario_v2(A)
        S2 = params.s2 or Decimal("300")
        S = ps.ontario_s(T4, V1, S2, Y)

    elif province == Province.BC:
        S2 = params.s2 or Decimal("575")
        S = ps.bc_s(A, T4, S2)

    T2 = T4 + V1 + V2 - S - p * LCP
    return max(ZERO, T2)
