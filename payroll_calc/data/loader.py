"""Parse CRA CSV files into structured data."""

import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Optional

from ..config import (
    CRA_DATA_PATH, YR, Province, PROVINCE_TO_CRA_CODE, TABLE81_CODE_TO_PROVINCE,
)
from .schema import (
    CraData, JurisdictionParams, TaxBracket, V1Tier, ClaimCode,
    CppParams, EiParams, QpipParams,
)


def _parse_decimal(s: str) -> Optional[Decimal]:
    """Parse a CRA-formatted number string to Decimal.

    Handles: "58,523", "0.14", "58,523.00", "$1,234.56", "No claim amount", "", "�"
    """
    s = s.strip().replace("$", "").replace(",", "").replace("\ufeff", "")
    if not s or s in ("No claim amount", "\ufffd", "�"):
        return None
    try:
        return Decimal(s)
    except InvalidOperation:
        return None


def _read_csv(path: Path) -> list[list[str]]:
    """Read CSV file, handling BOM and Windows-1252 encoding."""
    try:
        with open(path, encoding="utf-8-sig") as f:
            return list(csv.reader(f))
    except UnicodeDecodeError:
        with open(path, encoding="cp1252") as f:
            return list(csv.reader(f))


def _load_brackets(path: Path) -> tuple[JurisdictionParams, dict[str, JurisdictionParams]]:
    """Parse Table 8.1 (rtsncmtrshldcnstnt) into federal and provincial bracket data.

    Format: groups of 3 rows per jurisdiction:
      Row 1: Province, "A", threshold1, threshold2, ...
      Row 2: "",       "R"/"V", rate1, rate2, ...
      Row 3: "",       "K"/"KP", constant1, constant2, ...
    """
    rows = _read_csv(path)
    federal = JurisdictionParams()
    provinces: dict[str, JurisdictionParams] = {}

    i = 2  # skip header rows
    while i + 2 < len(rows):
        row_a = rows[i]
        row_r = rows[i + 1]
        row_k = rows[i + 2]

        jurisdiction = row_a[0].strip()
        if not jurisdiction:
            i += 1
            continue

        # Parse bracket values from columns 2 onward
        thresholds = [_parse_decimal(v) for v in row_a[2:] if v.strip()]
        rates = [_parse_decimal(v) for v in row_r[2:] if v.strip()]
        constants = [_parse_decimal(v) for v in row_k[2:] if v.strip()]

        # Filter out None values (empty trailing columns)
        thresholds = [t for t in thresholds if t is not None]
        rates = [r for r in rates if r is not None]
        constants = [c for c in constants if c is not None]

        n = min(len(thresholds), len(rates), len(constants))
        brackets = [
            TaxBracket(threshold=thresholds[j], rate=rates[j], constant=constants[j])
            for j in range(n)
        ]

        if jurisdiction == "Federal":
            federal.brackets = brackets
        elif jurisdiction in TABLE81_CODE_TO_PROVINCE:
            prov = TABLE81_CODE_TO_PROVINCE[jurisdiction]
            if prov.value not in provinces:
                provinces[prov.value] = JurisdictionParams()
            provinces[prov.value].brackets = brackets

        i += 3

    return federal, provinces


def _load_other_rates(path: Path, federal: JurisdictionParams,
                      provinces: dict[str, JurisdictionParams]) -> JurisdictionParams:
    """Parse Table 8.2 (thrrtsmnts) for other rates and amounts.

    Returns the 'outside Canada' params. Mutates federal and provinces in place.
    """
    rows = _read_csv(path)
    outside_canada = JurisdictionParams()

    # Column indices from header:
    # 0: jurisdiction, 1: Basic amount, 2: Index rate, 3: LCP rate, 4: LCP amount,
    # 5: CEA, 6: S2, 7: T4 to V1, 8: V1 rate, 9: Abatement, 10: Surtax

    i = 2  # skip header rows
    while i < len(rows):
        row = rows[i]
        if len(row) < 2:
            i += 1
            continue

        jurisdiction = row[0].strip()
        if not jurisdiction:
            i += 1
            continue

        basic_raw = row[1].strip() if len(row) > 1 else ""

        if jurisdiction == "Federal":
            federal.basic_personal_amount_label = "BPAF" if basic_raw == "BPAF" else None
            if basic_raw != "BPAF":
                federal.basic_personal_amount = _parse_decimal(basic_raw)
            federal.index_rate = _parse_decimal(row[2]) if len(row) > 2 else None
            federal.lcp_rate = _parse_decimal(row[3]) if len(row) > 3 else None
            federal.lcp_max = _parse_decimal(row[4]) if len(row) > 4 else None
            federal.cea = _parse_decimal(row[5]) if len(row) > 5 else None

        elif jurisdiction == "ON":
            params = provinces.setdefault("ON", JurisdictionParams())
            params.basic_personal_amount = _parse_decimal(basic_raw)
            params.index_rate = _parse_decimal(row[2]) if len(row) > 2 else None
            params.s2 = _parse_decimal(row[6]) if len(row) > 6 else None
            # Ontario has continuation rows for V1 tiers
            # First tier is on same row (may be 0 for the initial T4 threshold)
            v1_thresh = _parse_decimal(row[7]) if len(row) > 7 else None
            v1_rate = _parse_decimal(row[8]) if len(row) > 8 else None
            if v1_thresh is not None and v1_rate is not None and v1_rate > 0:
                params.v1_tiers.append(V1Tier(threshold=v1_thresh, rate=v1_rate))
            # Read continuation rows
            while i + 1 < len(rows) and not rows[i + 1][0].strip():
                i += 1
                cont = rows[i]
                t = _parse_decimal(cont[7]) if len(cont) > 7 else None
                r = _parse_decimal(cont[8]) if len(cont) > 8 else None
                if t is not None and r is not None:
                    params.v1_tiers.append(V1Tier(threshold=t, rate=r))

        elif jurisdiction == "QC":
            # Quebec - just store abatement
            federal.abatement = _parse_decimal(row[9]) if len(row) > 9 else None

        elif jurisdiction == "Outside Canada":
            outside_canada.surtax = _parse_decimal(row[10]) if len(row) > 10 else None

        elif jurisdiction in TABLE81_CODE_TO_PROVINCE:
            prov = TABLE81_CODE_TO_PROVINCE[jurisdiction]
            params = provinces.setdefault(prov.value, JurisdictionParams())

            if basic_raw in ("BPAMB", "BPAYT"):
                params.basic_personal_amount_label = basic_raw
            else:
                params.basic_personal_amount = _parse_decimal(basic_raw)

            params.index_rate = _parse_decimal(row[2]) if len(row) > 2 else None
            params.lcp_rate = _parse_decimal(row[3]) if len(row) > 3 else None
            params.lcp_max = _parse_decimal(row[4]) if len(row) > 4 else None
            params.cea = _parse_decimal(row[5]) if len(row) > 5 else None
            params.s2 = _parse_decimal(row[6]) if len(row) > 6 else None

        i += 1

    return outside_canada


def _load_claim_codes(path: Path) -> list[ClaimCode]:
    """Parse a claim code CSV (cc-*.csv)."""
    rows = _read_csv(path)
    codes = []

    for row in rows[2:]:  # skip 2 header rows
        if len(row) < 5:
            continue
        code_val = _parse_decimal(row[0])
        if code_val is None:
            continue

        codes.append(ClaimCode(
            code=int(code_val),
            tc_from=_parse_decimal(row[1]),
            tc_to=_parse_decimal(row[2]),
            tc=_parse_decimal(row[3]) or Decimal(0),
            k1=_parse_decimal(row[4]) or Decimal(0),
        ))

    return codes


def _load_cpp(data_path: Path) -> tuple[CppParams, CppParams]:
    """Load all 4 CPP CSV files and build CPP and QPP params."""
    # Table 8.3 - total
    ttl = _read_csv(data_path / f"cpp-qpp-ttl-01-{YR}e.csv")
    cpp_ttl = ttl[3]  # CPP row (skip title, header, sub-header)
    qpp_ttl = ttl[4]

    # Table 8.4 - base
    br = _read_csv(data_path / f"cpp-qpp-br-01-{YR}e.csv")
    cpp_br = br[2]  # CPP row
    qpp_br = br[3]

    # Table 8.5 - first additional
    addntl = _read_csv(data_path / f"cpp-qpp-addntl-01-{YR}e.csv")
    cpp_addntl = addntl[2]
    qpp_addntl = addntl[3]

    # Table 8.6 - second additional
    scnd = _read_csv(data_path / f"cpp-qpp-scnd-addntl-01-{YR}e.csv")
    cpp_scnd = scnd[2]
    qpp_scnd = scnd[3]

    def _build(ttl_row, br_row, addntl_row, scnd_row) -> CppParams:
        return CppParams(
            ympe=_parse_decimal(ttl_row[1]),
            basic_exemption=_parse_decimal(ttl_row[2]),
            ymce=_parse_decimal(ttl_row[3]),
            total_rate=_parse_decimal(ttl_row[4]),
            max_total=_parse_decimal(ttl_row[5]),
            base_rate=_parse_decimal(br_row[2]),
            max_base=_parse_decimal(br_row[3]),
            first_additional_rate=_parse_decimal(addntl_row[2]),
            max_first_additional=_parse_decimal(addntl_row[3]),
            yampe=_parse_decimal(scnd_row[2]),
            second_additional_rate=_parse_decimal(scnd_row[4]),
            max_second_additional=_parse_decimal(scnd_row[5]),
        )

    return _build(cpp_ttl, cpp_br, cpp_addntl, cpp_scnd), _build(qpp_ttl, qpp_br, qpp_addntl, qpp_scnd)


def _load_ei(data_path: Path) -> tuple[EiParams, EiParams]:
    """Load EI parameters (non-QC and QC)."""
    rows = _read_csv(data_path / f"ei-01-{YR}e.csv")
    # Row 2 = Canada except QC, Row 3 = QC

    def _build(row) -> EiParams:
        return EiParams(
            max_insurable=_parse_decimal(row[1]),
            employee_rate=_parse_decimal(row[2]),
            employer_rate=_parse_decimal(row[3]),
            max_employee_premium=_parse_decimal(row[4]),
            max_employer_premium=_parse_decimal(row[5]),
        )

    return _build(rows[2]), _build(rows[3])


def _load_qpip(data_path: Path) -> QpipParams:
    """Load QPIP parameters."""
    rows = _read_csv(data_path / f"qpip-01-{YR}e.csv")
    row = rows[2]
    return QpipParams(
        max_insurable=_parse_decimal(row[1]),
        employee_rate=_parse_decimal(row[2]),
        employer_rate=_parse_decimal(row[3]),
        max_employee_premium=_parse_decimal(row[4]),
        max_employer_premium=_parse_decimal(row[5]),
    )


def load_cra_data(data_path: Path = CRA_DATA_PATH) -> CraData:
    """Load all CRA CSV data into a CraData structure."""
    data = CraData()

    # Table 8.1 - brackets
    data.federal, data.provinces = _load_brackets(
        data_path / f"rtsncmtrshldcnstnt-01-{YR}e.csv"
    )

    # Table 8.2 - other rates
    data.outside_canada = _load_other_rates(
        data_path / f"thrrtsmnts-01-{YR}e.csv",
        data.federal,
        data.provinces,
    )

    # Claim codes - federal
    data.federal_claim_codes = _load_claim_codes(
        data_path / f"cc-fd-01-{YR}e.csv"
    )

    # Claim codes - provincial
    for prov in Province:
        cra_code = PROVINCE_TO_CRA_CODE[prov]
        data.provincial_claim_codes[prov.value] = _load_claim_codes(
            data_path / f"cc-{cra_code}-01-{YR}e.csv"
        )

    # CPP/QPP
    data.cpp, data.qpp = _load_cpp(data_path)

    # EI
    data.ei, data.ei_qc = _load_ei(data_path)

    # QPIP
    data.qpip = _load_qpip(data_path)

    return data
