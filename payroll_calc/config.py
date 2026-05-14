"""Enums, constants, and province code mappings for CRA payroll deductions."""

from enum import Enum
from pathlib import Path

YEAR = 2026
YR = "26"

CRA_DATA_PATH = Path(__file__).parent / "cra_data" / str(YEAR) / "csvs"


class Province(str, Enum):
    """Canadian provinces and territories (excluding Quebec for provincial tax)."""
    AB = "AB"
    BC = "BC"
    MB = "MB"
    NB = "NB"
    NL = "NL"
    NS = "NS"
    NT = "NT"
    NU = "NU"
    ON = "ON"
    PE = "PE"
    SK = "SK"
    YT = "YT"


class PayPeriod(int, Enum):
    """Standard pay period frequencies."""
    WEEKLY = 52
    BIWEEKLY = 26
    SEMI_MONTHLY = 24
    MONTHLY = 12


# CRA CSV filenames use non-standard province codes
PROVINCE_TO_CRA_CODE = {
    Province.AB: "ab",
    Province.BC: "bc",
    Province.MB: "mb",
    Province.NB: "nb",
    Province.NL: "nl",
    Province.NS: "ns",
    Province.NT: "nt",
    Province.NU: "nv",   # CRA uses 'nv' for Nunavut
    Province.ON: "on",
    Province.PE: "pei",  # CRA uses 'pei' for PEI
    Province.SK: "sk",
    Province.YT: "yt",
}

# CRA CSV province codes back to our enum (includes Federal)
CRA_CODE_TO_PROVINCE = {v: k for k, v in PROVINCE_TO_CRA_CODE.items()}

# Table 8.1 uses short codes without prefix
TABLE81_CODE_TO_PROVINCE = {
    "AB": Province.AB,
    "BC": Province.BC,
    "MB": Province.MB,
    "NB": Province.NB,
    "NL": Province.NL,
    "NS": Province.NS,
    "NT": Province.NT,
    "NU": Province.NU,
    "ON": Province.ON,
    "PE": Province.PE,
    "SK": Province.SK,
    "YT": Province.YT,
}

# T4032 table income step sizes per pay period
# CRA uses $8 for weekly; other periods scale proportionally (8 * P/52)
TABLE_STEP_SIZE = {
    PayPeriod.WEEKLY: 8,
    PayPeriod.BIWEEKLY: 16,
    PayPeriod.SEMI_MONTHLY: 18,
    PayPeriod.MONTHLY: 34,
}

# BPAF dynamic formula parameters (from T4127 PDF Chapter 2)
BPAF_MAX = "16452"
BPAF_MIN = "14829"
BPAF_CLAWBACK_START = "181440"
BPAF_CLAWBACK_END = "258482"
BPAF_CLAWBACK_AMOUNT = "1623"
BPAF_CLAWBACK_RANGE = "77042"

# BPAMB dynamic formula parameters
BPAMB_MAX = "15780"
BPAMB_CLAWBACK_START = "200000"
BPAMB_CLAWBACK_END = "400000"
