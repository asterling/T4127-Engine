"""
Download all CRA payroll deduction data for the current year.

Sources:
  - T4127 (Payroll Deductions Formulas): CSVs with rates, thresholds, claim codes
  - T4127 PDF: master formulas document for computer programs
  - T4032ON (Ontario Payroll Deductions Tables): PDFs with pre-computed lookup tables

All files are saved into ./cra_data/{year}/
"""

import requests
import datetime
import sys
from pathlib import Path

YEAR = datetime.date.today().year
YR = str(YEAR)[2:]  # e.g. "26"

# ── URL bases ──────────────────────────────────────────────────────────
T4127_CSV_BASE = "https://www.canada.ca/content/dam/cra-arc/formspubs/pub/t4127-jan"
T4032_PDF_BASE = f"https://www.canada.ca/content/dam/cra-arc/migration/cra-arc/tx/bsnss/tpcs/pyrll/t4032/{YEAR}"

# ── Province codes (as used in CRA CSV filenames) ─────────────────────
PROVINCE_CODES = [
    "fd",   # Federal
    "ab",   # Alberta
    "bc",   # British Columbia
    "mb",   # Manitoba
    "nb",   # New Brunswick
    "nl",   # Newfoundland & Labrador
    "ns",   # Nova Scotia
    "nt",   # Northwest Territories
    "nv",   # Nunavut (CRA uses 'nv', not 'nu')
    "on",   # Ontario
    "pei",  # Prince Edward Island (CRA uses 'pei', not 'pe')
    "sk",   # Saskatchewan
    "yt",   # Yukon
]

# ── CSV file list ─────────────────────────────────────────────────────
# Claim code tables (one per jurisdiction)
CLAIM_CODE_CSVS = [f"cc-{prov}-01-{YR}e.csv" for prov in PROVINCE_CODES]

# Rates, thresholds, CPP/QPP, EI tables
RATE_CSVS = [
    f"cpp-qpp-br-01-{YR}e.csv",          # CPP/QPP base rates
    f"cpp-qpp-ttl-01-{YR}e.csv",         # CPP/QPP total rates
    f"cpp-qpp-addntl-01-{YR}e.csv",      # CPP/QPP first additional
    f"cpp-qpp-scnd-addntl-01-{YR}e.csv", # CPP/QPP second additional
    f"ei-01-{YR}e.csv",                   # Employment Insurance
    f"qpip-01-{YR}e.csv",                # Quebec Parental Insurance Plan
    f"rtsncmtrshldcnstnt-01-{YR}e.csv",  # Rates, thresholds & constants
    f"thrrtsmnts-01-{YR}e.csv",          # Other rates and amounts
]

ALL_CSVS = CLAIM_CODE_CSVS + RATE_CSVS

# ── T4127 Formulas PDF ────────────────────────────────────────────────
T4127_FORMULA_PDF = f"t4127-01-{YR}e.pdf"

# ── T4032ON PDFs (Ontario tables) ────────────────────────────────────
# Section A: general info
# Section B(i): CPP contributions by pay period
# Section B(ii): CPP2 second additional
# Section C: EI premiums
# Section D+E: Federal + Ontario tax deductions by pay period
PAY_PERIODS = ["52", "26", "24", "12"]

T4032_ON_PDFS = (
    # Section A - general info
    [f"t4032-on-1-{YR}e.pdf"]
    # Section B(i) - CPP by pay period
    + [f"t4032cpp-{pp}pp-{YR}eng.pdf" for pp in PAY_PERIODS]
    # Section B(ii) - CPP2
    + [f"t4032cpp2-rpc2-{YR}eng.pdf"]
    # Section C - EI premiums
    + [f"t4032einoqc-{YR}eng.pdf"]
    # Section D+E - Federal + Ontario tax by pay period
    + [f"t4032-on-{pp}pp-{YR}-eng.pdf" for pp in PAY_PERIODS]
)


def download_file(url: str, dest: Path) -> bool:
    """Download a single file. Returns True on success."""
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        dest.write_bytes(r.content)
        return True
    except requests.RequestException as e:
        print(f"  FAILED: {e}", file=sys.stderr)
        return False


def download_all():
    data_dir = Path("cra_data") / str(YEAR)
    csv_dir = data_dir / "csvs"
    pdf_dir = data_dir / "pdfs"
    csv_dir.mkdir(parents=True, exist_ok=True)
    pdf_dir.mkdir(parents=True, exist_ok=True)

    ok, fail = 0, 0

    # ── CSVs from T4127 ──
    print(f"=== Downloading T4127 CSVs ({len(ALL_CSVS)} files) ===")
    for filename in ALL_CSVS:
        url = f"{T4127_CSV_BASE}/{filename}"
        print(f"  {filename} ...", end=" ")
        if download_file(url, csv_dir / filename):
            print("OK")
            ok += 1
        else:
            fail += 1

    # ── T4127 formulas PDF ──
    print(f"\n=== Downloading T4127 Formulas PDF ===")
    url = f"{T4127_CSV_BASE}/{T4127_FORMULA_PDF}"
    print(f"  {T4127_FORMULA_PDF} ...", end=" ")
    if download_file(url, pdf_dir / T4127_FORMULA_PDF):
        print("OK")
        ok += 1
    else:
        fail += 1

    # ── T4032ON PDFs ──
    print(f"\n=== Downloading T4032ON PDFs ({len(T4032_ON_PDFS)} files) ===")
    for filename in T4032_ON_PDFS:
        url = f"{T4032_PDF_BASE}/{filename}"
        print(f"  {filename} ...", end=" ")
        if download_file(url, pdf_dir / filename):
            print("OK")
            ok += 1
        else:
            fail += 1

    # ── Summary ──
    print(f"\nDone: {ok} succeeded, {fail} failed")
    print(f"Data saved to: {data_dir.resolve()}")
    return fail == 0


if __name__ == "__main__":
    success = download_all()
    sys.exit(0 if success else 1)
