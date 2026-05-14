# T4127 Engine

[![PyPI](https://img.shields.io/pypi/v/t4127-engine.svg)](https://pypi.org/project/t4127-engine/)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Tests: 92,035 passing](https://img.shields.io/badge/tests-92%2C035_passing-brightgreen.svg)](#accuracy--testing)
[![PDOC Validated](https://img.shields.io/badge/CRA_PDOC-penny--for--penny_match-brightgreen.svg)](#validate-against-the-cras-pdoc)
[![Tax Year: 2026](https://img.shields.io/badge/tax_year-2026-orange.svg)](#what-the-cra-actually-publishes)

**Open-source Canadian payroll deductions calculator.** Implements the CRA's T4127 formulas for all provinces and territories. Validated against 92,000+ test cases and penny-for-penny against the CRA's own PDOC calculator.

```
$1,000/week in Ontario, claim code 1:

  Federal tax:      $81.61
  Provincial tax:   $45.80
  CPP:              $55.50
  EI:               $16.30
  Total deductions: $199.21
```

## Quick Example

```python
from decimal import Decimal
from payroll_calc.calculator import calculate
from payroll_calc.data.loader import load_cra_data
from payroll_calc.config import Province, PayPeriod
from payroll_calc.models import DeductionRequest

cra = load_cra_data()

result = calculate(DeductionRequest(
    province=Province.ON,
    pay_period=PayPeriod.WEEKLY,
    gross_pay=Decimal("1000.00"),
), cra)

print(result.federal_tax)      # 81.61
print(result.provincial_tax)   # 45.80
print(result.cpp_total)        # 55.50
print(result.ei_premium)       # 16.30
print(result.total_deductions) # 199.21
```

## Why This Exists

Every Canadian employer is legally required to calculate payroll deductions using formulas published by the Canada Revenue Agency in a document called the [T4127](https://www.canada.ca/en/revenue-agency/services/forms-publications/payroll/t4127-payroll-deductions-formulas.html).

The formulas are public. The problem is how they're published.

The CRA distributes its payroll data as **21 CSV files buried across multiple web pages**, with inconsistent encoding (UTF-8 BOM, Windows-1252), comma-formatted numbers inside quoted fields, special tokens that require domain knowledge to interpret, and multi-row records that span 3 lines per province. The tax tables are locked inside **PDF files** that require scraping to validate against. The only official "calculator" is PDOC — a closed-source web app with no API, no batch mode, and no way to integrate it into anything.

There is no reference implementation. No open data API. No sample code. No test vectors.

A country with 2 million employers and a $1.2 trillion annual payroll base, and the government's answer is: *here are some PDFs and a web form, good luck*.

You have to wonder who benefits from this. It's certainly not small businesses and entrepreneurs, who are left choosing between paying a CPA hundreds of dollars a month, subscribing to payroll SaaS that charges per employee per pay run, or spending weeks deciphering a 70-page formula guide just to issue a paycheque. The complexity isn't accidental — it's a moat. Every layer of obscurity, every undocumented edge case, every PDF that should have been a CSV is another reason a small business owner gives up and hands their payroll to a vendor. The big accounting firms and payroll platforms aren't hurt by this — they thrive on it. They have teams of tax specialists and proprietary implementations they've built over decades. The opacity of the system is their competitive advantage, and the CRA's refusal to publish usable, machine-readable tax logic with reference implementations keeps that advantage locked in.

**T4127 Engine exists to change this.** If the CRA won't publish a reference implementation, the community can.

Part of the [Canada Pay Freedom](https://github.com/asterling) project. Licensed under [AGPL-3.0](LICENSE).

### Who is this for?

- **Payroll software developers** who need a correct, auditable calculation engine they can integrate into their product
- **HRIS and HR tech builders** who need a Canadian tax module without licensing a proprietary one
- **Accountants and bookkeepers** who want to verify their software's output against a transparent, testable implementation
- **Small business owners** who are tired of paying per-employee-per-month for what is fundamentally public arithmetic
- **Open-source projects** that need Canadian payroll support without reinventing the T4127 from scratch
- **Anyone** who believes tax calculation logic should be public infrastructure, not a proprietary black box

## Installation

### From PyPI

```bash
pip install t4127-engine
```

Then download the CRA's published rate data (21 CSV files fetched directly from canada.ca — not bundled in the package due to Crown copyright):

```bash
python -m payroll_calc.download_cra
```

### From source

```bash
git clone https://github.com/asterling/T4127-Engine.git
cd T4127-Engine
pip install -e ".[dev]"
python -m payroll_calc.download_cra
```

### Verify

```bash
python -m pytest payroll_calc/tests/test_regression.py -v
```

That's it. 43 tests, all passing in under a second.

## Usage

### From the command line

```bash
# Basic calculation
t4127 calculate --gross 1000 --province ON --period 52

# Output:
#   Gross pay:        $    1,000.00
#   Province:          ON (52pp, CC1/1)
#
#   Federal tax:      $       81.61
#   Provincial tax:   $       45.80
#   CPP:              $       55.50
#   EI:               $       16.30
#                     ─────────────
#   Total deductions: $      199.21
#   Net pay:          $      800.79

# With deductions
t4127 calculate --gross 3200 --province MB --period 26 --rpp 80 --union-dues 25

# JSON output (for piping to other tools)
t4127 calculate --gross 1000 --province ON --period 52 --json

# Download CRA data
t4127 download

# Compare against CRA's PDOC (requires Selenium + Chrome)
t4127 compare 1000 ON 52
```

### As a Python library

Load the CRA data once, then calculate as many pay periods as you need:

```python
from decimal import Decimal
from payroll_calc.calculator import calculate
from payroll_calc.data.loader import load_cra_data
from payroll_calc.config import Province, PayPeriod
from payroll_calc.models import DeductionRequest

cra = load_cra_data()

# Basic calculation — just province, pay period, and gross pay
result = calculate(DeductionRequest(
    province=Province.AB,
    pay_period=PayPeriod.BIWEEKLY,
    gross_pay=Decimal("3200.00"),
), cra)

# With RPP contributions and union dues
result = calculate(DeductionRequest(
    province=Province.MB,
    pay_period=PayPeriod.BIWEEKLY,
    gross_pay=Decimal("3200.00"),
    rpp_contributions=Decimal("80.00"),
    union_dues=Decimal("25.00"),
), cra)

# With a bonus
result = calculate(DeductionRequest(
    province=Province.ON,
    pay_period=PayPeriod.WEEKLY,
    gross_pay=Decimal("1000.00"),
    bonus=Decimal("5000.00"),
), cra)
print(result.bonus_tax)  # tax on the $5,000 bonus

# Mid-year with YTD tracking (for accurate CPP/EI cap calculations)
result = calculate(DeductionRequest(
    province=Province.ON,
    pay_period=PayPeriod.WEEKLY,
    gross_pay=Decimal("1000.00"),
    ytd_cpp=Decimal("3800.00"),
    ytd_ei=Decimal("1050.00"),
    ytd_pensionable=Decimal("70000.00"),
), cra)
# CPP/EI will be reduced or zero if annual maximums are reached
```

### As a REST API

```bash
uvicorn payroll_calc.main:app --port 8000
```

Interactive docs at `http://localhost:8000/docs`.

```bash
curl -X POST http://localhost:8000/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "province": "ON",
    "pay_period": 52,
    "gross_pay": "1000.00",
    "federal_claim_code": 1,
    "provincial_claim_code": 1
  }'
```

```json
{
  "federal_tax": "81.61",
  "provincial_tax": "45.80",
  "total_tax": "127.41",
  "cpp_total": "55.50",
  "cpp_base_portion": "46.17",
  "cpp2": "0.00",
  "ei_premium": "16.30",
  "total_deductions": "199.21",
  "bonus_tax": null,
  "annual_taxable_income": "51514.96",
  "basic_federal_tax": "4243.88",
  "annual_federal_tax": "4243.88",
  "basic_provincial_tax": "1781.51",
  "annual_provincial_tax": "2381.51"
}
```

### Validate against the CRA's PDOC

Compare our output penny-for-penny against the CRA's official Payroll Deductions Online Calculator (requires Selenium + Chrome):

```bash
pip install selenium
python -m payroll_calc.pdoc_query --compare 1000 ON 52
```

```
Field                             PDOC         Ours       Diff
--------------------------------------------------------------
Federal tax               $     81.61  $     81.61     +0.00
Provincial tax            $     45.80  $     45.80     +0.00
CPP                       $     55.50  $     55.50     +0.00
EI                        $     16.30  $     16.30     +0.00
Total deductions          $    199.21  $    199.21     +0.00

PERFECT MATCH
```

### Generate T4032 lookup tables

Download a T4032-style CSV lookup table (like the ones the CRA publishes as PDFs):

```bash
curl -o federal_weekly.csv http://localhost:8000/t4032/ON/52/federal.csv
curl -o provincial_biweekly.csv http://localhost:8000/t4032/ON/26/provincial.csv
```

## AI Agent Integration

T4127 Engine can be used as a tool by AI agents — give any LLM the ability to calculate Canadian payroll deductions.

### MCP Server (Claude Desktop, VS Code, Cursor)

Install with MCP support:

```bash
pip install t4127-engine[mcp]
t4127 download  # fetch CRA rate data
```

Add to your Claude Desktop config (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "payroll-calculator": {
      "command": "t4127-mcp"
    }
  }
}
```

Or run directly:

```bash
python -m payroll_calc.mcp_server
```

The server exposes two tools:
- **`calculate_payroll_deductions`** — full T4127 calculation with all optional parameters
- **`list_provinces`** — list supported provinces and territories

### OpenAI / Anthropic Function Calling

A ready-to-use tool schema is included at `payroll_calc/schemas/openai_tool.json`:

```python
import json
from pathlib import Path

# Load the schema
schema_path = Path("payroll_calc/schemas/openai_tool.json")
tools = json.loads(schema_path.read_text())

# Use with OpenAI
response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "What are the deductions on $5,000 biweekly in Alberta?"}],
    tools=tools,
)

# Use with Anthropic
response = client.messages.create(
    model="claude-sonnet-4-20250514",
    messages=[{"role": "user", "content": "What are the deductions on $5,000 biweekly in Alberta?"}],
    tools=[{"name": t["function"]["name"],
            "description": t["function"]["description"],
            "input_schema": t["function"]["parameters"]} for t in tools],
)
```

The schema defines the same parameters as the MCP server and CLI — you handle the actual function execution and return the result to the LLM.

## Supported Provinces & Pay Periods

**Provinces/territories:** AB, BC, MB, NB, NL, NS, NT, NU, ON, PE, SK, YT

**Pay periods:** Weekly (52), Biweekly (26), Semi-monthly (24), Monthly (12)

**Claim codes:** 0-10 (federal and provincial)

**Not yet supported:** Quebec provincial tax. Quebec administers its own provincial income tax through Revenu Québec using separate formulas (TP-1015.3), a separate pension plan (QPP instead of CPP), and a separate parental insurance plan (QPIP). Federal tax for Quebec employees *is* calculated (with the 16.5% abatement), but provincial deductions require a dedicated Revenu Québec implementation — this is on the roadmap.

## Roadmap

- **Quebec provincial tax** — Revenu Québec TP-1015.3 formulas, QPP, QPIP (the data is already downloaded, the formulas need implementing)
- **PyPI package** — `pip install t4127-engine` for easy integration
- **Annual rate updates** — automated workflow to pull new T4127 data when the CRA publishes each November
- **CPP/QPP edge cases** — employees turning 18 or 70 mid-year, multi-jurisdiction workers
- **GitHub Actions CI** — automated test runs on every push

See [CONTRIBUTING.md](CONTRIBUTING.md) if you want to help with any of these.

---

## Deep Dive

Everything below is for people who want to understand how the engine works, what data it uses, and how it's tested.

### What the CRA Actually Publishes

The T4127 Engine is built entirely from official CRA data. Here is exactly what the government provides and where — so you can verify we haven't made anything up.

The CRA publishes **21 CSV files** as part of the T4127 package. They are not linked from a single page or documented in a consistent format. The `download_cra.py` script fetches all of them from `canada.ca`:

#### Claim Code Tables (13 files)

One CSV per jurisdiction — maps claim codes 0-10 to total claim amounts (TC) and pre-computed tax credits (K1/K1P):

| File | Jurisdiction |
|------|-------------|
| `cc-fd-01-26e.csv` | Federal |
| `cc-ab-01-26e.csv` | Alberta |
| `cc-bc-01-26e.csv` | British Columbia |
| `cc-mb-01-26e.csv` | Manitoba |
| `cc-nb-01-26e.csv` | New Brunswick |
| `cc-nl-01-26e.csv` | Newfoundland & Labrador |
| `cc-ns-01-26e.csv` | Nova Scotia |
| `cc-nt-01-26e.csv` | Northwest Territories |
| `cc-nv-01-26e.csv` | Nunavut (CRA uses `nv`, not `nu`) |
| `cc-on-01-26e.csv` | Ontario |
| `cc-pei-01-26e.csv` | Prince Edward Island (CRA uses `pei`, not `pe`) |
| `cc-sk-01-26e.csv` | Saskatchewan |
| `cc-yt-01-26e.csv` | Yukon |

#### Rate and Threshold Tables (8 files)

| File | T4127 Table | Contents |
|------|------------|----------|
| `rtsncmtrshldcnstnt-01-26e.csv` | Table 8.1 | Tax brackets for all jurisdictions — 3 rows per province (thresholds, rates, constants). This is the core of the income tax calculation. |
| `thrrtsmnts-01-26e.csv` | Table 8.2 | Basic personal amounts, index rates, LCP credits, CEA, Ontario surtax (V1) tiers, and other jurisdiction-specific amounts. |
| `cpp-qpp-br-01-26e.csv` | Table 8.4 | CPP/QPP base contribution rates and annual maximums |
| `cpp-qpp-ttl-01-26e.csv` | Table 8.3 | CPP/QPP total rates, YMPE ($74,600), basic exemption ($3,500), max contributions |
| `cpp-qpp-addntl-01-26e.csv` | Table 8.5 | CPP/QPP first additional contribution (1% rate, $711 max) |
| `cpp-qpp-scnd-addntl-01-26e.csv` | Table 8.6 | CPP2 second additional contribution — YAMPE ($85,000), 4% rate, $416 max |
| `ei-01-26e.csv` | Table 8.7 | Employment Insurance rates and maximums (separate rows for QC and non-QC) |
| `qpip-01-26e.csv` | Table 8.8 | Quebec Parental Insurance Plan rates (for future Quebec support) |

#### What the CRA does NOT publish

- No reference implementation in any programming language
- No machine-readable API for PDOC (the online calculator)
- No test vectors or expected output for given inputs
- No versioned data releases or changelogs for rate updates
- No standardized format — the 21 CSVs use inconsistent encodings, non-standard province codes (`nv` for Nunavut, `pei` for PEI), comma-formatted numbers inside quoted fields, special tokens (`BPAF`, `BPAMB`, `No claim amount`), and multi-row records with no delimiter

All of these are parsed by `data/loader.py`, which handles every encoding quirk and format inconsistency we've encountered.

### How the Calculation Works

The engine implements all 6 steps of the T4127 Option 1 formulas:

| Step | Module | What It Computes |
|------|--------|-----------------|
| Prereq | `formulas/cpp.py` | CPP base + first additional + CPP2 contributions |
| Prereq | `formulas/ei.py` | EI premiums |
| 1 | `formulas/annual_income.py` | Annual taxable income: `A = P x (I - F - F2 - F5A - U1) - HD - F1` |
| 2-3 | `formulas/federal_tax.py` | Basic federal tax `T3` and annual federal tax `T1` |
| 4-5 | `formulas/provincial_tax.py` | Basic provincial tax `T4` and annual provincial tax `T2` |
| 6 | `formulas/per_period_tax.py` | Per-period deduction: `T = (T1 + T2) / P + L` |

Supporting modules:

| Module | Purpose |
|--------|---------|
| `formulas/credits.py` | Tax credits K1-K4 (federal) and K1P-K5P (provincial) |
| `formulas/bpaf.py` | Dynamic basic personal amounts — BPAF clawback ($181,440-$258,482), BPAMB ($200,000-$400,000), BPAYT |
| `formulas/province_specific.py` | Ontario surtax (V1), Ontario Health Premium (V2), Ontario/BC tax reductions (S), Alberta K5P |
| `formulas/bonus.py` | Bonus/retroactive pay: `TB = (T1+T2 with bonus) - (T1+T2 without bonus)` |

The main entry point is `calculator.py`, which orchestrates all steps in order and returns a `DeductionResponse` with every intermediate value.

### Features

- **Full T4127 Option 1** — all 6 steps for salary, wages, and non-periodic payments
- **CPP/CPP2/EI** — base CPP, first additional CPP, second additional CPP (CPP2), and EI
- **Dynamic BPAF/BPAMB/BPAYT** — income-dependent basic personal amounts for federal, Manitoba, and Yukon
- **Province-specific rules** — Ontario surtax (V1), Ontario Health Premium (V2), Ontario/BC tax reductions (S), Alberta supplemental credit (K5P), labour-sponsored funds credits (LCP) for MB, NB, NS, SK
- **Bonus/retroactive pay** — differential tax calculation on non-periodic payments
- **T4032 table generation** — produces CSV files matching the CRA's published lookup tables
- **Decimal precision** — all arithmetic uses `decimal.Decimal` with CRA-specific rounding rules

### Accuracy & Testing

#### 92,035 tests

| Test Suite | Count | What It Validates |
|-----------|-------|-------------------|
| `test_regression.py` | 43 | CRA data parsing, CPP/EI calculations, all provinces, all pay periods, claim code ordering, BPAF formulas, bonus tax |
| `test_t4032_exhaustive.py` | 91,992 | Every row in all 8 T4032ON PDF tables (4 pay periods x federal + provincial), tested at midpoint + 2 random points per range, across all claim codes |

#### PDOC penny-for-penny match

| Gross Pay | Province | Period | Federal Tax | Provincial Tax | Total Deductions | PDOC Match |
|-----------|----------|--------|-------------|----------------|------------------|------------|
| $1,000/wk | ON | 52pp | $81.61 | $45.80 | $199.21 | Exact |
| $3,000/wk | ON | 52pp | $514.60 | $301.03 | $1,039.03 | Exact |
| $5,000/wk | ON | 52pp | $1,073.23 | $690.74 | $2,138.97 | Exact |
| $20,000/mo | ON | 12pp | $4,172.15 | $2,654.48 | $8,325.28 | Exact |

#### Why T4032 tables show larger differences at high incomes

Below YMPE (~$74,600/year annualized), our calculator and the T4032 PDF tables agree within **$1.50/period**. Above YMPE, differences grow to $5-$70 because the T4032 tables don't properly handle the CPP annual cap. The CRA acknowledges this:

> "If at any point during the year, the employee reaches the YMPE of $74,600 [...] we recommend using the PDOC for more accurate calculations."

Our calculator matches PDOC exactly — the T4032 discrepancies are a limitation of the lookup tables, not our formulas.

### API Reference

#### `POST /calculate`

All fields except `province`, `pay_period`, and `gross_pay` are optional and default to sensible values (claim code 1, zero deductions, zero YTD).

**Request body:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `province` | string | *required* | `AB`, `BC`, `MB`, `NB`, `NL`, `NS`, `NT`, `NU`, `ON`, `PE`, `SK`, `YT` |
| `pay_period` | int | *required* | `52`, `26`, `24`, or `12` |
| `gross_pay` | decimal | *required* | Gross remuneration for the pay period |
| `federal_claim_code` | int | `1` | Federal claim code (0-10) |
| `provincial_claim_code` | int | `1` | Provincial claim code (0-10) |
| `pensionable_earnings` | decimal | gross_pay | If different from gross pay |
| `insurable_earnings` | decimal | gross_pay | If different from gross pay |
| `rpp_contributions` | decimal | `0` | RPP/RRSP contributions per period |
| `union_dues` | decimal | `0` | Union dues per period |
| `prescribed_zone` | decimal | `0` | Annual prescribed zone deduction |
| `annual_deductions` | decimal | `0` | Annual deductions (child care, support payments) |
| `additional_tax` | decimal | `0` | Additional tax per period (TD1 request) |
| `bonus` | decimal | `0` | Bonus or retroactive pay this period |
| `ytd_cpp` | decimal | `0` | Year-to-date CPP contributions |
| `ytd_cpp2` | decimal | `0` | Year-to-date CPP2 contributions |
| `ytd_ei` | decimal | `0` | Year-to-date EI premiums |
| `ytd_pensionable` | decimal | `0` | Year-to-date pensionable earnings |
| `dependants_for_reduction` | decimal | `0` | Ontario tax reduction dependant amount |
| `cpp_months` | int | `12` | Months CPP contributions required |

**Response body:**

| Field | Description |
|-------|-------------|
| `federal_tax` | Federal income tax for the period |
| `provincial_tax` | Provincial income tax for the period |
| `total_tax` | Combined federal + provincial |
| `cpp_total` | CPP contribution (base + first additional) |
| `cpp_base_portion` | Base CPP portion (used in K2 credit) |
| `cpp2` | CPP2 second additional contribution |
| `ei_premium` | Employment insurance premium |
| `total_deductions` | Sum of all deductions |
| `bonus_tax` | Tax on the bonus (null if no bonus) |
| `annual_taxable_income` | Annualized taxable income (A) |
| `basic_federal_tax` | Basic federal tax (T3) |
| `annual_federal_tax` | Annual federal tax (T1) |
| `basic_provincial_tax` | Basic provincial tax (T4) |
| `annual_provincial_tax` | Annual provincial tax (T2) |

#### `GET /t4032/{province}/{pay_period}/{table_type}.csv`

Generate a T4032-style CSV. `table_type` is `federal` or `provincial`. Returns CSV with columns: `From`, `Less than`, `CC 0` through `CC 10`.

#### `GET /provinces`

List all supported provinces.

#### `GET /claim-codes/{jurisdiction}`

Claim code table for `federal` or a province code (e.g., `ON`).

### Project Structure

```
T4127-Engine/
├── README.md
├── LICENSE                          AGPL-3.0
├── CONTRIBUTING.md
├── pyproject.toml
│
└── payroll_calc/
    ├── __init__.py                  Package init, __version__
    ├── calculator.py                Main engine — orchestrates all T4127 steps
    ├── config.py                    Province/PayPeriod enums, CRA code mappings
    ├── models.py                    Pydantic request/response models
    ├── rounding.py                  CRA-specific rounding (ROUND_HALF_UP, truncation)
    ├── main.py                      FastAPI app entry point
    ├── download_cra.py              Downloads all CRA CSVs and PDFs from canada.ca
    ├── pdoc_query.py                Selenium PDOC scraper for validation
    │
    ├── data/
    │   ├── schema.py                Dataclasses: TaxBracket, ClaimCode, CppParams, etc.
    │   └── loader.py                CSV parser — handles all CRA encoding quirks
    │
    ├── formulas/
    │   ├── annual_income.py         Step 1: annual taxable income (A)
    │   ├── federal_tax.py           Steps 2-3: T3, T1
    │   ├── provincial_tax.py        Steps 4-5: T4, T2
    │   ├── per_period_tax.py        Step 6: per-period tax (T)
    │   ├── credits.py               Tax credits K1-K4, K1P-K5P
    │   ├── cpp.py                   CPP/CPP2 contributions
    │   ├── ei.py                    EI premiums
    │   ├── bpaf.py                  Dynamic BPAF/BPAMB/BPAYT
    │   ├── province_specific.py     ON surtax/OHP, BC reduction, AB K5P
    │   └── bonus.py                 Bonus/retroactive pay tax
    │
    ├── tables/
    │   └── t4032_generator.py       Generates T4032-style CSV lookup tables
    │
    ├── api/
    │   └── routes.py                FastAPI route definitions
    │
    ├── tests/
    │   ├── test_regression.py       43 regression tests
    │   ├── test_t4032_exhaustive.py 91,992 exhaustive PDF validation tests
    │   ├── extract_pdf_reference.py PDF table extractor
    │   └── reference_data/          Extracted T4032ON tables (8 JSON files)
    │
    └── cra_data/                    Downloaded CRA data (gitignored)
        └── 2026/
            ├── csvs/                21 CSV files
            └── pdfs/                12 PDF files
```

### CRA Data Sources

| Source | Edition | URL |
|--------|---------|-----|
| T4127 Payroll Deductions Formulas | 122nd, Jan 2026 | [canada.ca](https://www.canada.ca/en/revenue-agency/services/forms-publications/payroll/t4127-payroll-deductions-formulas/t4127-jan.html) |
| T4032ON Payroll Deductions Tables | Jan 2026 | [canada.ca](https://www.canada.ca/en/revenue-agency/services/forms-publications/payroll/t4032-payroll-deductions-tables/t4032on-jan.html) |
| PDOC Online Calculator | 2026 | [canada.ca](https://www.canada.ca/en/revenue-agency/services/e-services/digital-services-businesses/payroll-deductions-online-calculator.html) |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and PR guidelines.

## License

[AGPL-3.0](LICENSE) — free to use, modify, and deploy. If you modify and deploy it as a service, you must share your changes.
