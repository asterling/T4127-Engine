"""Generate T4032-style payroll deduction lookup tables as CSV.

Reproduces the same tables found in the T4032ON PDFs:
- Federal tax deductions by income range and claim code
- Provincial tax deductions by income range and claim code
"""

import csv
import io
from decimal import Decimal

from ..config import Province, PayPeriod, TABLE_STEP_SIZE
from ..data.schema import CraData
from ..calculator import calculate_for_table

ZERO = Decimal(0)

# Maximum annual income to generate tables for (~$265,000 / year)
MAX_ANNUAL_INCOME = Decimal("265000")


def generate_t4032_table(
    province: Province,
    pay_period: PayPeriod,
    cra: CraData,
    table_type: str = "federal",
    max_annual: Decimal = MAX_ANNUAL_INCOME,
) -> str:
    """Generate a T4032-style CSV table.

    Args:
        province: Province/territory
        pay_period: Pay period frequency
        cra: Loaded CRA data
        table_type: "federal" or "provincial"
        max_annual: Maximum annual income to cover

    Returns:
        CSV string with columns: From, Less than, CC0, CC1, ..., CC10
    """
    P = pay_period.value
    step = TABLE_STEP_SIZE[pay_period]
    p_dec = Decimal(P)
    step_dec = Decimal(step)

    # Income range per period
    max_period_income = int(max_annual / p_dec) + step
    # Start from a reasonable minimum (where tax starts being > 0 for CC1)
    min_period_income = _find_table_start(province, pay_period, cra, table_type)

    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    header = ["From", "Less than"] + [f"CC {i}" for i in range(11)]
    writer.writerow(header)

    income_low = min_period_income
    while income_low < max_period_income:
        income_high = income_low + step
        midpoint = Decimal(income_low) + step_dec / 2

        row = [str(income_low), str(income_high)]

        for cc in range(11):
            fed, prov = calculate_for_table(
                income=midpoint,
                P=P,
                province=province,
                federal_claim_code=cc,
                provincial_claim_code=cc,
                cra=cra,
            )
            if table_type == "federal":
                val = fed
            else:
                val = prov

            # Format: show .00 amounts, suppress negative/zero for high claim codes
            if val <= ZERO:
                row.append("")
            else:
                row.append(f"{val:.2f}")

        writer.writerow(row)
        income_low += step

    return output.getvalue()


def _find_table_start(
    province: Province,
    pay_period: PayPeriod,
    cra: CraData,
    table_type: str,
) -> int:
    """Find the starting income for the table (where CC0 first produces tax > 0).

    Binary search for the lowest income where claim code 0 yields positive tax.
    """
    P = pay_period.value
    step = TABLE_STEP_SIZE[pay_period]

    low = 0
    high = 2000  # reasonable upper bound for starting point

    while low < high:
        mid = (low + high) // 2
        midpoint = Decimal(mid) + Decimal(step) / 2
        fed, prov = calculate_for_table(midpoint, P, province, 0, 0, cra)
        val = fed if table_type == "federal" else prov
        if val > ZERO:
            high = mid
        else:
            low = mid + step

    # Align to step boundary
    return (low // step) * step
