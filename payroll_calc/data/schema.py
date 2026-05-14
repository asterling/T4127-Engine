"""Data structures for parsed CRA payroll deduction data."""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional


@dataclass
class TaxBracket:
    """One bracket from Table 8.1 (threshold/rate/constant)."""
    threshold: Decimal
    rate: Decimal
    constant: Decimal


@dataclass
class V1Tier:
    """Ontario surtax tier (T4 threshold and rate)."""
    threshold: Decimal
    rate: Decimal


@dataclass
class JurisdictionParams:
    """Parameters for a jurisdiction from Tables 8.1 + 8.2."""
    # Table 8.1: tax brackets
    brackets: list[TaxBracket] = field(default_factory=list)
    # Table 8.2: other rates and amounts
    basic_personal_amount: Optional[Decimal] = None  # None means dynamic (BPAF/BPAMB/BPAYT)
    basic_personal_amount_label: Optional[str] = None  # "BPAF", "BPAMB", "BPAYT" if dynamic
    index_rate: Optional[Decimal] = None
    lcp_rate: Optional[Decimal] = None
    lcp_max: Optional[Decimal] = None
    cea: Optional[Decimal] = None        # Canada Employment Amount
    s2: Optional[Decimal] = None         # Basic amount for tax reduction (BC, ON)
    v1_tiers: list[V1Tier] = field(default_factory=list)  # Ontario surtax
    abatement: Optional[Decimal] = None  # Quebec 16.5%
    surtax: Optional[Decimal] = None     # Outside Canada 48%


@dataclass
class ClaimCode:
    """One claim code entry from cc-*.csv."""
    code: int
    tc_from: Optional[Decimal]  # None for "No claim amount"
    tc_to: Optional[Decimal]
    tc: Decimal       # Total claim amount (Option 1 TCP)
    k1: Decimal       # Non-refundable tax credit (K1 or K1P)


@dataclass
class CppParams:
    """CPP/QPP parameters from the 4 CPP CSV files."""
    # From cpp-qpp-ttl (Table 8.3)
    ympe: Decimal             # Year's Maximum Pensionable Earnings
    basic_exemption: Decimal  # $3,500
    ymce: Decimal             # Year's Maximum Contributory Earnings
    total_rate: Decimal       # Employee + employer total contribution rate
    max_total: Decimal        # Maximum total contribution
    # From cpp-qpp-br (Table 8.4)
    base_rate: Decimal
    max_base: Decimal
    # From cpp-qpp-addntl (Table 8.5)
    first_additional_rate: Decimal
    max_first_additional: Decimal
    # From cpp-qpp-scnd-addntl (Table 8.6)
    yampe: Decimal            # Year's Additional Maximum Pensionable Earnings
    second_additional_rate: Decimal
    max_second_additional: Decimal


@dataclass
class EiParams:
    """EI parameters from ei CSV (Table 8.7)."""
    max_insurable: Decimal
    employee_rate: Decimal
    employer_rate: Decimal
    max_employee_premium: Decimal
    max_employer_premium: Decimal


@dataclass
class QpipParams:
    """QPIP parameters from qpip CSV (Table 8.8)."""
    max_insurable: Decimal
    employee_rate: Decimal
    employer_rate: Decimal
    max_employee_premium: Decimal
    max_employer_premium: Decimal


@dataclass
class CraData:
    """Top-level container for all parsed CRA data."""
    # Federal brackets and params
    federal: JurisdictionParams = field(default_factory=JurisdictionParams)
    # Provincial/territorial brackets and params
    provinces: dict[str, JurisdictionParams] = field(default_factory=dict)  # key = Province enum value
    # Outside Canada
    outside_canada: JurisdictionParams = field(default_factory=JurisdictionParams)
    # Claim codes: jurisdiction code -> list of ClaimCode
    federal_claim_codes: list[ClaimCode] = field(default_factory=list)
    provincial_claim_codes: dict[str, list[ClaimCode]] = field(default_factory=dict)
    # CPP (non-QC) and QPP
    cpp: Optional[CppParams] = None
    qpp: Optional[CppParams] = None
    # EI (non-QC and QC)
    ei: Optional[EiParams] = None
    ei_qc: Optional[EiParams] = None
    # QPIP
    qpip: Optional[QpipParams] = None
