"""MCP server for Canadian payroll deductions calculator.

Exposes T4127 Engine as tools for AI agents via the Model Context Protocol.
Works with Claude Desktop, VS Code, Cursor, and any MCP-compatible client.

Usage:
    python -m payroll_calc.mcp_server
    # or via entry point:
    t4127-mcp
"""

from decimal import Decimal
from typing import Optional

from mcp.server.fastmcp import FastMCP

from .calculator import calculate
from .config import Province, PayPeriod
from .data.loader import load_cra_data
from .models import DeductionRequest

# Load CRA rate data once at startup (~50ms)
_cra = load_cra_data()

PROVINCE_NAMES = {
    "AB": "Alberta",
    "BC": "British Columbia",
    "MB": "Manitoba",
    "NB": "New Brunswick",
    "NL": "Newfoundland and Labrador",
    "NS": "Nova Scotia",
    "NT": "Northwest Territories",
    "NU": "Nunavut",
    "ON": "Ontario",
    "PE": "Prince Edward Island",
    "SK": "Saskatchewan",
    "YT": "Yukon",
}

server = FastMCP("T4127 Engine — Canadian Payroll Deductions Calculator")


def _to_decimal(value: Optional[float]) -> Optional[Decimal]:
    if value is None:
        return None
    return Decimal(str(value))


def _serialize_response(resp) -> dict:
    """Convert DeductionResponse to a JSON-safe dict with string money values."""
    return {
        "federal_tax": str(resp.federal_tax),
        "provincial_tax": str(resp.provincial_tax),
        "total_tax": str(resp.total_tax),
        "cpp": str(resp.cpp_total),
        "cpp2": str(resp.cpp2),
        "ei": str(resp.ei_premium),
        "total_deductions": str(resp.total_deductions),
        "bonus_tax": str(resp.bonus_tax) if resp.bonus_tax else None,
        "annual_taxable_income": str(resp.annual_taxable_income),
        "basic_federal_tax": str(resp.basic_federal_tax),
        "annual_federal_tax": str(resp.annual_federal_tax),
        "basic_provincial_tax": str(resp.basic_provincial_tax),
        "annual_provincial_tax": str(resp.annual_provincial_tax),
    }


@server.tool()
def calculate_payroll_deductions(
    gross_pay: float,
    province: str,
    pay_period: int,
    federal_claim_code: int = 1,
    provincial_claim_code: int = 1,
    bonus: float = 0,
    rpp_contributions: float = 0,
    union_dues: float = 0,
    prescribed_zone: float = 0,
    annual_deductions: float = 0,
    additional_tax: float = 0,
    ytd_cpp: float = 0,
    ytd_cpp2: float = 0,
    ytd_ei: float = 0,
    ytd_pensionable: float = 0,
    pensionable_earnings: Optional[float] = None,
    insurable_earnings: Optional[float] = None,
    dependants_for_reduction: float = 0,
    cpp_months: int = 12,
) -> dict:
    """Calculate Canadian payroll deductions for a single pay period.

    Computes federal tax, provincial tax, CPP, CPP2, and EI using the CRA's
    T4127 formulas. Supports all provinces and territories except Quebec
    provincial tax (Quebec uses separate Revenu Québec formulas).

    Args:
        gross_pay: Gross pay for the period in CAD (e.g., 1000.00)
        province: Two-letter province code (AB, BC, MB, NB, NL, NS, NT, NU, ON, PE, SK, YT)
        pay_period: Pay periods per year (52=weekly, 26=biweekly, 24=semi-monthly, 12=monthly)
        federal_claim_code: Federal TD1 claim code 0-10 (default 1 = basic personal amount)
        provincial_claim_code: Provincial TD1 claim code 0-10 (default 1)
        bonus: Bonus or retroactive pay this period (triggers differential tax method)
        rpp_contributions: RPP/RRSP contributions per period
        union_dues: Union dues per period
        prescribed_zone: Annual prescribed northern zone deduction
        annual_deductions: Other annual deductions (child care, support payments)
        additional_tax: Extra tax per period requested on TD1
        ytd_cpp: Year-to-date CPP contributions (for mid-year cap calculations)
        ytd_cpp2: Year-to-date CPP2 contributions
        ytd_ei: Year-to-date EI premiums
        ytd_pensionable: Year-to-date pensionable earnings
        pensionable_earnings: Pensionable earnings for the period (defaults to gross_pay)
        insurable_earnings: Insurable earnings for the period (defaults to gross_pay)
        dependants_for_reduction: Ontario only — dependant amount for tax reduction
        cpp_months: Months CPP required, 1-12 (for employees turning 18 or 70 mid-year)

    Returns:
        Dict with per-period deductions (federal_tax, provincial_tax, cpp, ei,
        total_deductions) and annual breakdown. All monetary values as strings
        for exact decimal precision.
    """
    province_str = province.upper()
    try:
        prov = Province(province_str)
    except ValueError:
        valid = ", ".join(p.value for p in Province)
        return {"error": f"Unknown province '{province_str}'. Valid: {valid}"}

    try:
        pp = PayPeriod(pay_period)
    except ValueError:
        return {"error": f"Invalid pay period {pay_period}. Valid: 52, 26, 24, 12"}

    req = DeductionRequest(
        province=prov,
        pay_period=pp,
        gross_pay=Decimal(str(gross_pay)),
        federal_claim_code=federal_claim_code,
        provincial_claim_code=provincial_claim_code,
        bonus=Decimal(str(bonus)),
        rpp_contributions=Decimal(str(rpp_contributions)),
        union_dues=Decimal(str(union_dues)),
        prescribed_zone=Decimal(str(prescribed_zone)),
        annual_deductions=Decimal(str(annual_deductions)),
        additional_tax=Decimal(str(additional_tax)),
        ytd_cpp=Decimal(str(ytd_cpp)),
        ytd_cpp2=Decimal(str(ytd_cpp2)),
        ytd_ei=Decimal(str(ytd_ei)),
        ytd_pensionable=Decimal(str(ytd_pensionable)),
        pensionable_earnings=_to_decimal(pensionable_earnings),
        insurable_earnings=_to_decimal(insurable_earnings),
        dependants_for_reduction=Decimal(str(dependants_for_reduction)),
        cpp_months=cpp_months,
    )

    result = calculate(req, _cra)
    return _serialize_response(result)


@server.tool()
def list_provinces() -> list[dict]:
    """List the Canadian provinces and territories supported by the calculator.

    Quebec is excluded because it administers its own provincial tax through
    Revenu Québec using separate formulas (TP-1015.3).

    Returns:
        List of dicts with 'code' and 'name' for each supported province.
    """
    return [{"code": p.value, "name": PROVINCE_NAMES[p.value]} for p in Province]


def main():
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
