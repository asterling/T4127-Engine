"""Pydantic models for API request/response."""

from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

from .config import Province, PayPeriod

ZERO = Decimal(0)


class DeductionRequest(BaseModel):
    """Input for payroll deduction calculation."""

    province: Province
    pay_period: PayPeriod
    gross_pay: Decimal = Field(description="Gross remuneration for the pay period (I)")

    federal_claim_code: int = Field(default=1, ge=0, le=10)
    provincial_claim_code: int = Field(default=1, ge=0, le=10)

    # Optional overrides (default to gross_pay)
    pensionable_earnings: Optional[Decimal] = Field(
        default=None, description="PI - defaults to gross_pay if not set"
    )
    insurable_earnings: Optional[Decimal] = Field(
        default=None, description="IE - defaults to gross_pay if not set"
    )

    # Deductions
    rpp_contributions: Decimal = Field(default=ZERO, description="F - RPP/RRSP contributions per period")
    union_dues: Decimal = Field(default=ZERO, description="U1 - union dues per period")
    prescribed_zone: Decimal = Field(default=ZERO, description="HD - annual prescribed zone deduction")
    annual_deductions: Decimal = Field(default=ZERO, description="F1 - annual deductions")
    additional_tax: Decimal = Field(default=ZERO, description="L - additional tax per period")

    # Bonus (non-periodic payment)
    bonus: Decimal = Field(default=ZERO, description="B - bonus/retroactive pay this period")

    # YTD tracking (optional, for mid-year accuracy)
    ytd_cpp: Decimal = Field(default=ZERO, description="D - YTD CPP contributions")
    ytd_cpp2: Decimal = Field(default=ZERO, description="D2 - YTD CPP2 contributions")
    ytd_ei: Decimal = Field(default=ZERO, description="D1 - YTD EI premiums")
    ytd_pensionable: Decimal = Field(default=ZERO, description="PIYTD")

    # Ontario-specific
    dependants_for_reduction: Decimal = Field(
        default=ZERO, description="Y - Ontario tax reduction dependant amount"
    )

    # CPP months
    cpp_months: int = Field(default=12, ge=1, le=12, description="PM - months CPP required")


class DeductionResponse(BaseModel):
    """Output of payroll deduction calculation."""

    # Per-period deductions
    federal_tax: Decimal
    provincial_tax: Decimal
    total_tax: Decimal

    cpp_total: Decimal
    cpp_base_portion: Decimal
    cpp2: Decimal
    ei_premium: Decimal

    total_deductions: Decimal

    bonus_tax: Optional[Decimal] = None

    # Annual breakdown for transparency
    annual_taxable_income: Decimal   # A
    basic_federal_tax: Decimal       # T3
    annual_federal_tax: Decimal      # T1
    basic_provincial_tax: Decimal    # T4
    annual_provincial_tax: Decimal   # T2
