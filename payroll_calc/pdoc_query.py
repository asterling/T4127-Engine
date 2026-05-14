"""Query the CRA Payroll Deductions Online Calculator (PDOC) via Selenium.

Automates the multi-step PDOC web form to calculate payroll deductions
for a given salary, province, and pay period. Used to validate our
calculator against the CRA's official tool.

Usage:
    python -m payroll_calc.pdoc_query 1000 ON 52
    python -m payroll_calc.pdoc_query 5000 AB 26
    python -m payroll_calc.pdoc_query --compare 1000 ON 52   # compare with our calc

Requires: selenium, Chrome/Chromium
"""

import re
import sys
import time
from dataclasses import dataclass
from decimal import Decimal

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select


# ── Province/pay period mappings to PDOC select values ────────────────

PROVINCE_TO_PDOC = {
    "AB": "ALBERTA", "BC": "BRITISH_COLUMBIA", "MB": "MANITOBA",
    "NB": "NEW_BRUNSWICK", "NL": "NEWFOUNDLAND_AND_LABRADOR",
    "NS": "NOVA_SCOTIA", "NT": "NORTHWEST_TERRITORIES", "NU": "NUNAVUT",
    "ON": "ONTARIO", "PE": "PRINCE_EDWARD_ISLAND", "SK": "SASKATCHEWAN",
    "YT": "YUKON",
}

PAY_PERIOD_TO_PDOC = {
    52: "WEEKLY_52PP", 26: "BI_WEEKLY", 24: "SEMI_MONTHLY", 12: "MONTHLY_12PP",
}

PDOC_URL = "https://apps.cra-arc.gc.ca/ebci/rhpd/beta/entry/en"


@dataclass
class PdocResult:
    """Parsed PDOC calculation results."""
    federal_tax: Decimal
    provincial_tax: Decimal
    total_tax: Decimal
    cpp: Decimal
    cpp2: Decimal
    ei: Decimal
    total_deductions: Decimal
    net_amount: Decimal


# ── Selenium helpers ──────────────────────────────────────────────────

def _create_driver():
    o = Options()
    o.add_argument("--headless=new")
    o.add_argument(
        "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    )
    o.add_argument("--disable-blink-features=AutomationControlled")
    o.add_argument("--window-size=1920,1080")
    d = webdriver.Chrome(options=o)
    d.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'},
    )
    return d


def _js(d, code):
    d.execute_script(code)


def _click_next(d):
    _js(d, """document.querySelectorAll('button').forEach(b => {
        var t = b.textContent.toLowerCase();
        if (t.includes('next') || t.includes('calculate')) b.click();
    })""")


def _set_select_by_label(d, label_contains, value):
    for s in d.find_elements(By.TAG_NAME, "select"):
        sid = s.get_attribute("id")
        labs = d.find_elements(By.CSS_SELECTOR, f'label[for="{sid}"]')
        if labs and label_contains.lower() in labs[0].text.lower():
            Select(s).select_by_value(value)
            return


def _set_input_by_label(d, label_contains, value):
    for inp in d.find_elements(By.CSS_SELECTOR, "input[type=text], input[type=number]"):
        iid = inp.get_attribute("id")
        labs = d.find_elements(By.CSS_SELECTOR, f'label[for="{iid}"]')
        if labs and label_contains.lower() in labs[0].text.lower():
            inp.clear()
            inp.send_keys(str(value))
            return


def _click_radio(d, group_contains, value):
    for fs in d.find_elements(By.TAG_NAME, "fieldset"):
        leg = fs.find_elements(By.TAG_NAME, "legend")
        if leg and group_contains.lower() in leg[0].text.lower():
            for r in fs.find_elements(By.CSS_SELECTOR, "input[type=radio]"):
                if r.get_attribute("value") == value:
                    _js(d, f"document.getElementById('{r.get_attribute('id')}').click()")
                    return


def _set_date(d, year="2026", month="03", day="15"):
    for s in d.find_elements(By.TAG_NAME, "select"):
        sid = s.get_attribute("id") or ""
        opts = [o.text for o in s.find_elements(By.TAG_NAME, "option")]
        if "Year" in sid or (opts and opts[0] == "Year"):
            Select(s).select_by_value(year)
        elif "January" in opts:
            Select(s).select_by_value(month)
        elif opts and opts[0] == "Day":
            Select(s).select_by_value(day)


# ── Main query function ──────────────────────────────────────────────

def query_pdoc(province: str, pay_period: int, gross_pay: str) -> PdocResult:
    """Query the CRA PDOC for payroll deductions.

    Uses claim code 1 (basic personal amount), no YTD amounts,
    no additional deductions — matching our calculator's defaults.

    Args:
        province: Province code (e.g., "ON")
        pay_period: Pay periods per year (52, 26, 24, 12)
        gross_pay: Gross salary per period (e.g., "1000")

    Returns:
        PdocResult with all deduction amounts
    """
    d = _create_driver()
    try:
        # ── Entry: select Salary ──
        d.get(PDOC_URL)
        time.sleep(8)
        _js(d, "document.querySelector('input[value=SALARY]').click()")
        time.sleep(1)
        _click_next(d)
        time.sleep(5)

        # ── Step 1: Employee info ──
        _set_input_by_label(d, "employee", "Adam Sterling")
        _set_input_by_label(d, "employer", "Test Corp")
        _set_select_by_label(d, "province", PROVINCE_TO_PDOC[province])
        _set_select_by_label(d, "pay period", PAY_PERIOD_TO_PDOC[pay_period])
        _set_date(d)
        time.sleep(1)
        _click_next(d)
        time.sleep(5)

        # ── Step 2: Income ──
        _set_input_by_label(d, "salary", gross_pay)
        _click_radio(d, "bonus", "NO_BONUS_PAY_NO_RETROACTIVE_PAY")
        _click_radio(d, "qpp", "FALSE")
        _click_radio(d, "clergy", "FALSE")
        time.sleep(1)
        _click_next(d)
        time.sleep(5)

        # ── Step 3: TD1 / deductions — accept defaults (claim code 1) ──
        _click_next(d)
        time.sleep(5)

        # ── Results page ──
        if "results" not in d.current_url:
            raise RuntimeError(f"Expected results page, got: {d.current_url}")

        return _parse_results(d)

    finally:
        d.quit()


def _parse_results(d) -> PdocResult:
    """Parse the PDOC results page."""
    body = d.find_element(By.TAG_NAME, "body").text
    lines = body.split("\n")

    def _find(label: str) -> Decimal:
        for line in lines:
            if label.lower() in line.lower():
                amounts = re.findall(r"([\d,]+\.\d{2})", line)
                if amounts:
                    return Decimal(amounts[-1].replace(",", ""))
        return Decimal("0")

    return PdocResult(
        federal_tax=_find("Federal tax deduction"),
        provincial_tax=_find("Provincial tax deduction"),
        total_tax=_find("Total tax deductions"),
        cpp=_find("CPP deductions"),
        cpp2=_find("CPP2 deductions"),
        ei=_find("EI deductions"),
        total_deductions=_find("Total deductions"),
        net_amount=_find("Net amount"),
    )


# ── Comparison with our calculator ───────────────────────────────────

def compare_with_calculator(province: str, pay_period: int, gross_pay: str):
    """Query PDOC and compare results with our calculator."""
    from .data.loader import load_cra_data
    from .calculator import calculate
    from .models import DeductionRequest
    from .config import Province as ProvEnum, PayPeriod as PPEnum

    print(f"Querying PDOC: {province}, {pay_period}pp, ${gross_pay} ...")
    pdoc = query_pdoc(province, pay_period, gross_pay)

    print(f"Running our calculator ...")
    cra = load_cra_data()
    req = DeductionRequest(
        province=ProvEnum(province),
        pay_period=PPEnum(pay_period),
        gross_pay=Decimal(gross_pay),
        federal_claim_code=1,
        provincial_claim_code=1,
    )
    ours = calculate(req, cra)

    # Compare
    print(f"\n{'Field':<25s} {'PDOC':>12s} {'Ours':>12s} {'Diff':>10s}")
    print("-" * 62)

    comparisons = [
        ("Federal tax", pdoc.federal_tax, ours.federal_tax),
        ("Provincial tax", pdoc.provincial_tax, ours.provincial_tax),
        ("Total tax", pdoc.total_tax, ours.total_tax),
        ("CPP", pdoc.cpp, ours.cpp_total),
        ("CPP2", pdoc.cpp2, ours.cpp2),
        ("EI", pdoc.ei, ours.ei_premium),
        ("Total deductions", pdoc.total_deductions, ours.total_deductions),
    ]

    all_match = True
    for label, pdoc_val, our_val in comparisons:
        diff = our_val - pdoc_val
        marker = "" if abs(diff) < Decimal("0.02") else " ***"
        if abs(diff) >= Decimal("0.02"):
            all_match = False
        print(f"{label:<25s} ${str(pdoc_val):>10s}  ${str(our_val):>10s}  {float(diff):>+8.2f}{marker}")

    print()
    if all_match:
        print("PERFECT MATCH")
    else:
        print("DIFFERENCES FOUND (marked with ***)")

    return pdoc, ours


if __name__ == "__main__":
    args = sys.argv[1:]

    compare_mode = False
    if args and args[0] == "--compare":
        compare_mode = True
        args = args[1:]

    gross = args[0] if len(args) > 0 else "1000"
    province = args[1] if len(args) > 1 else "ON"
    pp = int(args[2]) if len(args) > 2 else 52

    if compare_mode:
        compare_with_calculator(province, pp, gross)
    else:
        print(f"Querying PDOC: {province}, {pp}pp, ${gross}")
        result = query_pdoc(province, pp, gross)
        print(f"\nResults:")
        print(f"  Federal tax:      ${result.federal_tax}")
        print(f"  Provincial tax:   ${result.provincial_tax}")
        print(f"  Total tax:        ${result.total_tax}")
        print(f"  CPP:              ${result.cpp}")
        print(f"  CPP2:             ${result.cpp2}")
        print(f"  EI:               ${result.ei}")
        print(f"  Total deductions: ${result.total_deductions}")
        print(f"  Net amount:       ${result.net_amount}")
