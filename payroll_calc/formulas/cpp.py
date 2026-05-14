"""Chapter 6 — CPP/CPP2 contribution formulas."""

from decimal import Decimal

from ..data.schema import CppParams
from ..rounding import round_tax, truncate_2dp

ZERO = Decimal(0)
TWELVE = Decimal(12)


def calc_cpp_period(
    pi: Decimal,
    P: int,
    cpp: CppParams,
    D: Decimal = ZERO,
    PM: int = 12,
) -> tuple[Decimal, Decimal]:
    """Calculate CPP base + first additional contributions for a pay period.

    Args:
        pi: Pensionable earnings this period (gross + taxable benefits)
        P: Number of pay periods in the year
        cpp: CPP parameters
        D: Year-to-date total CPP contributions (base + first additional)
        PM: Months CPP contributions required (default 12)

    Returns:
        (C_total, C_base_portion) where:
          C_total = total CPP contribution this period (base + first additional)
          C_base_portion = just the base portion (needed for K2 credit calculation)
    """
    p = Decimal(P)
    pm = Decimal(PM)

    basic_exemption_period = truncate_2dp(cpp.basic_exemption / p)

    # Total contribution (base + first additional combined)
    max_annual = cpp.max_total * (pm / TWELVE)
    C = min(
        max(ZERO, max_annual - D),
        max(ZERO, cpp.total_rate * (pi - basic_exemption_period)),
    )
    C = round_tax(C)

    # Base portion for K2 credit: C * (base_rate / total_rate)
    # T4127: "no rounding on this division"
    C_base = C * (cpp.base_rate / cpp.total_rate)

    return C, C_base


def calc_cpp2_period(
    pi: Decimal,
    P: int,
    cpp: CppParams,
    piytd: Decimal = ZERO,
    D2: Decimal = ZERO,
    PM: int = 12,
) -> Decimal:
    """Calculate CPP2 (second additional) contributions for a pay period.

    CPP2 only applies when earnings exceed YMPE.

    Args:
        pi: Pensionable earnings this period
        P: Number of pay periods
        cpp: CPP parameters
        piytd: Year-to-date pensionable earnings (before this period)
        D2: Year-to-date CPP2 contributions
        PM: Months CPP contributions required

    Returns:
        C2 = CPP2 contribution this period
    """
    pm = Decimal(PM)

    # W = greater of PIYTD and YMPE*(PM/12)
    W = max(piytd, cpp.ympe * (pm / TWELVE))

    max_annual_c2 = cpp.max_second_additional * (pm / TWELVE)

    C2 = min(
        max(ZERO, max_annual_c2 - D2),
        max(ZERO, (piytd + pi - W) * cpp.second_additional_rate),
    )
    C2 = round_tax(C2)

    return C2


def calc_f5(C: Decimal, C2: Decimal, cpp: CppParams) -> Decimal:
    """Calculate F5 (additional CPP contribution deduction for taxable income).

    F5 = C × (first_additional_rate / total_rate) + C2
    """
    if C == ZERO and C2 == ZERO:
        return ZERO
    return C * (cpp.first_additional_rate / cpp.total_rate) + C2


def calc_f5a_f5b(F5: Decimal, pi: Decimal, bonus: Decimal) -> tuple[Decimal, Decimal]:
    """Split F5 between periodic (F5A) and non-periodic (F5B) portions.

    F5A = F5 × ((PI - B) / PI)
    F5B = F5 × (B / PI)
    """
    if pi == ZERO:
        return ZERO, ZERO
    if bonus == ZERO:
        return F5, ZERO

    f5a = F5 * ((pi - bonus) / pi)
    f5b = F5 * (bonus / pi)
    return f5a, f5b
