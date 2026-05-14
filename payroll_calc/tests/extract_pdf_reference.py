"""Extract T4032ON PDF tables into JSON reference data for regression testing.

Parses every row from all 8 tables (4 pay periods × federal/provincial) in the
T4032ON PDFs and writes them to tests/reference_data/.

Run from the mini-projects root:
    python -m payroll_calc.tests.extract_pdf_reference
"""

import json
import re
import subprocess
from pathlib import Path

PDF_DIR = Path(__file__).parent.parent / "cra_data" / "2026" / "pdfs"
OUT_DIR = Path(__file__).parent / "reference_data"

PAY_PERIODS = {
    52: "t4032-on-52pp-26-eng.pdf",
    26: "t4032-on-26pp-26-eng.pdf",
    24: "t4032-on-24pp-26-eng.pdf",
    12: "t4032-on-12pp-26-eng.pdf",
}

# Regex for a table row: "from - to  val val val ..."
# Handles rows where leading values are present and trailing may be empty
ROW_RE = re.compile(
    r"^\s*(\d+)\s+-\s+(\d+)\s+([\d.]+(?:\s+[\d.]+)*)\s*$"
)

# Regex for the very first row (below minimum, only CC0 has a value):
# "             370        * (1)         .00"
FIRST_ROW_RE = re.compile(
    r"^\s+(\d+)\s+\*\s*\(1\)\s+([\d.]+)"
)


def extract_text(pdf_path: Path) -> str:
    result = subprocess.run(
        ["pdftotext", "-layout", str(pdf_path), "-"],
        capture_output=True, text=True,
    )
    return result.stdout


def parse_table_section(lines: list[str]) -> list[dict]:
    """Parse one section (federal or provincial) of a PDF into row dicts."""
    rows = []

    for line in lines:
        # Try normal row
        m = ROW_RE.match(line)
        if m:
            from_val = int(m.group(1))
            to_val = int(m.group(2))
            # Split the values — they're space-separated
            raw_vals = m.group(3).split()
            # Values are right-aligned to CC columns. Empty leading columns mean
            # those claim codes have no tax. The values fill from CC0 rightward,
            # but empty slots appear as missing (not "0"). We need to figure out
            # which CCs these values correspond to.
            #
            # The PDF always shows values left-to-right starting from CC0.
            # If fewer than 11 values, the missing ones are at the RIGHT (higher CCs).
            values = {}
            for i, v in enumerate(raw_vals):
                try:
                    values[i] = float(v)
                except ValueError:
                    pass

            rows.append({
                "from": from_val,
                "to": to_val,
                "values": values,
            })

    return rows


def assign_cc_columns(rows: list[dict]) -> list[dict]:
    """Assign CC column indices to parsed values.

    The PDF layout means values are positionally aligned. When a row has fewer
    than 11 values, the MISSING columns are at the right (higher claim codes)
    where tax would be zero or negative.

    However, at low incomes, CC0 may have tax but CC1+ may not, and as income
    rises, more CCs get values. The values always start from CC0.
    """
    result = []
    for row in rows:
        cc_values = {}
        for idx, val in row["values"].items():
            cc_values[idx] = val
        result.append({
            "from": row["from"],
            "to": row["to"],
            "cc": cc_values,
        })
    return result


def split_federal_provincial(text: str) -> tuple[str, str]:
    """Split PDF text into federal and provincial sections."""
    lines = text.split("\n")

    # Find where provincial starts
    prov_start = None
    for i, line in enumerate(lines):
        if "provincial tax deductions" in line.lower() and "ontario" in line.lower():
            prov_start = i
            break

    if prov_start is None:
        raise ValueError("Could not find provincial section in PDF")

    fed_lines = lines[:prov_start]
    prov_lines = lines[prov_start:]

    return fed_lines, prov_lines


def filter_data_lines(lines: list[str]) -> list[str]:
    """Filter to only lines that contain table data rows."""
    result = []
    for line in lines:
        # Skip headers, footers, page markers
        if any(skip in line for skip in [
            "Federal tax", "Ontario provincial", "Effective",
            "Also look up", "Pay", "From Less", "CC ",
            "D-", "E-", "the ''Pay''", "Step-by-step",
            "pay periods", "(1)",
        ]):
            continue
        if ROW_RE.match(line):
            result.append(line)
    return result


def extract_all():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for pp, filename in PAY_PERIODS.items():
        pdf_path = PDF_DIR / filename
        if not pdf_path.exists():
            print(f"SKIP: {filename} not found")
            continue

        print(f"Processing {filename} ({pp}pp)...")
        text = extract_text(pdf_path)

        fed_lines, prov_lines = split_federal_provincial(text)

        fed_data = filter_data_lines(fed_lines)
        prov_data = filter_data_lines(prov_lines)

        fed_rows = assign_cc_columns(parse_table_section(fed_data))
        prov_rows = assign_cc_columns(parse_table_section(prov_data))

        print(f"  Federal: {len(fed_rows)} rows")
        print(f"  Provincial: {len(prov_rows)} rows")

        # Save as JSON
        for table_type, rows in [("federal", fed_rows), ("provincial", prov_rows)]:
            out_path = OUT_DIR / f"t4032on_{pp}pp_{table_type}.json"
            with open(out_path, "w") as f:
                json.dump(rows, f, indent=2)
            print(f"  Wrote {out_path.name}")


if __name__ == "__main__":
    extract_all()
