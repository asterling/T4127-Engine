"""Tax credit calculations (K1-K4, K1P-K5P).

From T4127 Steps 2-5.
"""

from decimal import Decimal
from typing import Optional

from ..data.schema import CraData, CppParams, EiParams, ClaimCode
from ..rounding import round_tax

ZERO = Decimal(0)


def get_claim_code(codes: list[ClaimCode], code: int) -> ClaimCode:
    """Look up a claim code by number."""
    for cc in codes:
        if cc.code == code:
            return cc
    raise ValueError(f"Invalid claim code: {code}")


def calc_k1(federal_claim_code: ClaimCode) -> Decimal:
    """Federal non-refundable personal tax credit. Pre-computed in CSV."""
    return federal_claim_code.k1


def calc_k2(
    C: Decimal,
    EI: Decimal,
    P: int,
    cpp: CppParams,
    ei: EiParams,
    PM: int = 12,
) -> Decimal:
    """Federal CPP/EI tax credit.

    K2 = 0.14 × (annualized CPP base portion + annualized EI)
    Capped at maximum annual amounts.
    """
    R1 = Decimal("0.14")  # lowest federal rate
    p = Decimal(P)
    pm = Decimal(PM)

    # Annualized CPP base portion: P × C × (base_rate / total_rate)
    # Capped at max_base × (PM/12)
    cpp_base_annual = min(
        p * C * (cpp.base_rate / cpp.total_rate),
        cpp.max_base * (pm / Decimal(12)),
    )

    # Annualized EI: P × EI, capped at max premium
    ei_annual = min(p * EI, ei.max_employee_premium)

    return R1 * cpp_base_annual + R1 * ei_annual


def calc_k4(A: Decimal, cea: Decimal) -> Decimal:
    """Federal Canada Employment Amount credit.

    K4 = 0.14 × min(A, CEA)
    """
    R1 = Decimal("0.14")
    return R1 * min(A, cea)


def calc_k1p(provincial_claim_code: ClaimCode) -> Decimal:
    """Provincial non-refundable personal tax credit. Pre-computed in CSV."""
    return provincial_claim_code.k1


def calc_k2p(
    C: Decimal,
    EI: Decimal,
    P: int,
    lowest_prov_rate: Decimal,
    cpp: CppParams,
    ei: EiParams,
    PM: int = 12,
) -> Decimal:
    """Provincial CPP/EI tax credit.

    Same as K2 but using the province's lowest tax rate.
    """
    p = Decimal(P)
    pm = Decimal(PM)

    cpp_base_annual = min(
        p * C * (cpp.base_rate / cpp.total_rate),
        cpp.max_base * (pm / Decimal(12)),
    )
    ei_annual = min(p * EI, ei.max_employee_premium)

    return lowest_prov_rate * cpp_base_annual + lowest_prov_rate * ei_annual


def calc_k4p_yukon(A: Decimal, cea: Decimal) -> Decimal:
    """Yukon Canada Employment Amount credit.

    K4P = 0.064 × min(A, CEA)
    """
    return Decimal("0.064") * min(A, cea)


def calc_k5p_alberta(k1p: Decimal, k2p: Decimal) -> Decimal:
    """Alberta supplemental non-refundable tax credit.

    K5P = max(0, (K1P + K2P - $4,896) × 0.25)
    """
    return max(ZERO, (k1p + k2p - Decimal("4896")) * Decimal("0.25"))
