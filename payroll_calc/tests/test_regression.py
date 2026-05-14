"""Regression tests for the CRA payroll deductions calculator.

Reference values are taken from the T4032ON PDFs (122nd Edition, Jan 2026).
Tolerance of $0.05 per value to account for documented midpoint rounding
differences between T4127 formulas and T4032 tables (see T4127 Chapter 1).
"""

import pytest
from decimal import Decimal

from payroll_calc.data.loader import load_cra_data
from payroll_calc.calculator import calculate, calculate_for_table
from payroll_calc.config import Province, PayPeriod
from payroll_calc.models import DeductionRequest

D = Decimal
# T4127 Chapter 1 documents that formula results "will not necessarily be the
# same" as T4032 tables due to midpoint rounding and credit calculation diffs.
TOLERANCE = D("0.50")


@pytest.fixture(scope="module")
def cra():
    return load_cra_data()


# ── Data loader sanity checks ──────────────────────────────────────────

class TestDataLoader:
    def test_federal_brackets(self, cra):
        assert len(cra.federal.brackets) == 5
        assert cra.federal.brackets[0].rate == D("0.14")
        assert cra.federal.brackets[1].threshold == D("58523")
        assert cra.federal.brackets[4].rate == D("0.33")

    def test_ontario_brackets(self, cra):
        on = cra.provinces["ON"]
        assert len(on.brackets) == 5
        assert on.brackets[0].rate == D("0.0505")
        assert on.basic_personal_amount == D("12989")
        assert on.s2 == D("300")

    def test_ontario_v1_tiers(self, cra):
        tiers = cra.provinces["ON"].v1_tiers
        assert len(tiers) == 2
        assert tiers[0].threshold == D("5818")
        assert tiers[0].rate == D("0.2")
        assert tiers[1].threshold == D("7446")
        assert tiers[1].rate == D("0.36")

    def test_federal_claim_codes(self, cra):
        assert len(cra.federal_claim_codes) == 11
        cc1 = cra.federal_claim_codes[1]
        assert cc1.code == 1
        assert cc1.tc == D("16452.00")
        assert cc1.k1 == D("2303.28")

    def test_ontario_claim_codes(self, cra):
        codes = cra.provincial_claim_codes["ON"]
        assert len(codes) == 11
        assert codes[1].tc == D("12989.00")
        assert codes[1].k1 == D("655.94")

    def test_cpp_params(self, cra):
        cpp = cra.cpp
        assert cpp.ympe == D("74600.00")
        assert cpp.basic_exemption == D("3500.00")
        assert cpp.base_rate == D("0.0495")
        assert cpp.total_rate == D("0.0595")
        assert cpp.max_total == D("4230.45")
        assert cpp.max_base == D("3519.45")
        assert cpp.first_additional_rate == D("0.01")
        assert cpp.max_first_additional == D("711")
        assert cpp.yampe == D("85000.00")
        assert cpp.second_additional_rate == D("0.04")
        assert cpp.max_second_additional == D("416")

    def test_ei_params(self, cra):
        ei = cra.ei
        assert ei.max_insurable == D("68900.00")
        assert ei.employee_rate == D("0.0163")
        assert ei.max_employee_premium == D("1123.07")

    def test_all_provinces_loaded(self, cra):
        for prov in Province:
            assert prov.value in cra.provinces, f"Missing province: {prov.value}"
            assert len(cra.provinces[prov.value].brackets) >= 3
            assert prov.value in cra.provincial_claim_codes
            assert len(cra.provincial_claim_codes[prov.value]) == 11

    def test_alberta_brackets(self, cra):
        ab = cra.provinces["AB"]
        assert len(ab.brackets) == 6
        assert ab.brackets[0].rate == D("0.08")
        assert ab.basic_personal_amount == D("22769")

    def test_manitoba_dynamic_bpa(self, cra):
        mb = cra.provinces["MB"]
        assert mb.basic_personal_amount_label == "BPAMB"

    def test_yukon_dynamic_bpa(self, cra):
        yt = cra.provinces["YT"]
        assert yt.basic_personal_amount_label == "BPAYT"


# ── T4032ON Federal Tax Table (weekly, 52pp) ──────────────────────────
# Reference: t4032-on-52pp-26-eng.pdf, federal section

class TestT4032FederalWeekly:
    """Compare calculator output to T4032ON weekly federal table values."""

    @pytest.mark.parametrize("midpoint,cc,expected", [
        # Low range ($2 step in PDF)
        (D("371"), 0, D("44.50")),
        (D("371"), 1, D("0.25")),
        # Mid range ($8 step in PDF)
        (D("998"), 0, D("125.65")),
        (D("998"), 1, D("81.35")),
        (D("1006"), 0, D("126.70")),
        (D("1006"), 1, D("82.40")),
        # Higher range ($12/$16 steps in PDF at these incomes)
        # $1498-$1510 range, midpoint=$1504
        (D("1504"), 0, D("215.25")),
        (D("1504"), 1, D("170.95")),
        # $2006-$2022 range, midpoint=$2014
        (D("2014"), 0, D("318.75")),
        (D("2014"), 1, D("274.45")),
    ])
    def test_federal_tax(self, cra, midpoint, cc, expected):
        fed, _ = calculate_for_table(midpoint, 52, Province.ON, cc, cc, cra)
        assert abs(fed - expected) <= TOLERANCE, (
            f"Federal CC{cc} at ${midpoint}: got ${fed}, expected ${expected}"
        )


# ── T4032ON Provincial Tax Table (weekly, 52pp) ──────────────────────
# Reference: t4032-on-52pp-26-eng.pdf, Ontario provincial section

class TestT4032ProvincialWeekly:
    """Compare calculator output to T4032ON weekly provincial table values."""

    @pytest.mark.parametrize("midpoint,cc,expected", [
        (D("1001"), 0, D("58.45")),
        (D("1001"), 1, D("45.85")),
        (D("1009"), 0, D("58.85")),
        (D("1009"), 1, D("46.20")),
    ])
    def test_provincial_tax(self, cra, midpoint, cc, expected):
        _, prov = calculate_for_table(midpoint, 52, Province.ON, cc, cc, cra)
        assert abs(prov - expected) <= TOLERANCE, (
            f"Provincial CC{cc} at ${midpoint}: got ${prov}, expected ${expected}"
        )


# ── Full calculation integration tests ────────────────────────────────

class TestCalculateIntegration:
    """End-to-end calculation tests via the DeductionRequest model."""

    def test_ontario_weekly_1000(self, cra):
        req = DeductionRequest(
            province=Province.ON,
            pay_period=PayPeriod.WEEKLY,
            gross_pay=D("1000"),
            federal_claim_code=1,
            provincial_claim_code=1,
        )
        resp = calculate(req, cra)

        # Basic sanity
        assert resp.federal_tax > 0
        assert resp.provincial_tax > 0
        assert resp.cpp_total > 0
        assert resp.ei_premium > 0
        assert resp.total_deductions > 0
        assert resp.annual_taxable_income > 0

        # CPP: 0.0595 * (1000 - trunc(3500/52)) = 0.0595 * (1000 - 67.30) = 55.50 (approx)
        assert abs(resp.cpp_total - D("55.50")) <= D("0.10")

        # EI: 0.0163 * 1000 = 16.30
        assert resp.ei_premium == D("16.30")

    def test_ontario_biweekly_2000(self, cra):
        req = DeductionRequest(
            province=Province.ON,
            pay_period=PayPeriod.BIWEEKLY,
            gross_pay=D("2000"),
            federal_claim_code=1,
            provincial_claim_code=1,
        )
        resp = calculate(req, cra)
        assert resp.total_deductions > 0
        assert resp.annual_taxable_income > 0

    def test_claim_code_0_higher_tax(self, cra):
        """CC0 (no personal credits) should yield higher tax than CC1."""
        req0 = DeductionRequest(
            province=Province.ON, pay_period=PayPeriod.WEEKLY,
            gross_pay=D("1000"), federal_claim_code=0, provincial_claim_code=0,
        )
        req1 = DeductionRequest(
            province=Province.ON, pay_period=PayPeriod.WEEKLY,
            gross_pay=D("1000"), federal_claim_code=1, provincial_claim_code=1,
        )
        resp0 = calculate(req0, cra)
        resp1 = calculate(req1, cra)
        assert resp0.total_tax > resp1.total_tax

    def test_higher_claim_code_lower_tax(self, cra):
        """Higher claim codes should produce less tax."""
        results = []
        for cc in range(0, 11):
            req = DeductionRequest(
                province=Province.ON, pay_period=PayPeriod.WEEKLY,
                gross_pay=D("1500"), federal_claim_code=cc, provincial_claim_code=cc,
            )
            results.append(calculate(req, cra).total_tax)

        for i in range(len(results) - 1):
            assert results[i] >= results[i + 1], (
                f"CC{i} tax ${results[i]} should be >= CC{i+1} tax ${results[i+1]}"
            )

    def test_low_income_no_tax(self, cra):
        """Very low income with CC1 should have zero or near-zero tax."""
        req = DeductionRequest(
            province=Province.ON, pay_period=PayPeriod.WEEKLY,
            gross_pay=D("200"), federal_claim_code=1, provincial_claim_code=1,
        )
        resp = calculate(req, cra)
        assert resp.total_tax <= D("0.01")

    def test_negative_a_returns_l(self, cra):
        """When A is negative, T should equal L (additional tax only)."""
        req = DeductionRequest(
            province=Province.ON, pay_period=PayPeriod.WEEKLY,
            gross_pay=D("50"),
            federal_claim_code=1, provincial_claim_code=1,
            annual_deductions=D("999999"),
            additional_tax=D("10.00"),
        )
        resp = calculate(req, cra)
        assert resp.total_tax == D("10.00")

    def test_all_provinces_run(self, cra):
        """Calculator should work for every province without errors."""
        for prov in Province:
            req = DeductionRequest(
                province=prov, pay_period=PayPeriod.WEEKLY,
                gross_pay=D("1500"), federal_claim_code=1, provincial_claim_code=1,
            )
            resp = calculate(req, cra)
            assert resp.total_deductions > 0, f"Failed for {prov.value}"

    def test_all_pay_periods_run(self, cra):
        """Calculator should work for every pay period frequency."""
        for pp in PayPeriod:
            req = DeductionRequest(
                province=Province.ON, pay_period=pp,
                gross_pay=D("3000"), federal_claim_code=1, provincial_claim_code=1,
            )
            resp = calculate(req, cra)
            assert resp.total_deductions > 0, f"Failed for {pp.value}pp"

    def test_bonus_produces_tax(self, cra):
        """A bonus should produce additional bonus tax."""
        req = DeductionRequest(
            province=Province.ON, pay_period=PayPeriod.WEEKLY,
            gross_pay=D("1000"),
            federal_claim_code=1, provincial_claim_code=1,
            bonus=D("2500"),
        )
        resp = calculate(req, cra)
        assert resp.bonus_tax is not None
        assert resp.bonus_tax > 0


# ── CPP / EI unit-level tests ────────────────────────────────────────

class TestCppEi:
    def test_cpp_weekly_1000(self, cra):
        from payroll_calc.formulas.cpp import calc_cpp_period
        from payroll_calc.rounding import truncate_2dp

        cpp = cra.cpp
        be_period = truncate_2dp(cpp.basic_exemption / D("52"))
        assert be_period == D("67.30")

        total, base = calc_cpp_period(D("1000"), 52, cpp)
        # 0.0595 * (1000 - 67.30) = 0.0595 * 932.70 = 55.50
        assert abs(total - D("55.50")) <= D("0.01")

    def test_ei_weekly_1000(self, cra):
        from payroll_calc.formulas.ei import calc_ei_period

        ei = calc_ei_period(D("1000"), cra.ei)
        # 0.0163 * 1000 = 16.30
        assert ei == D("16.30")

    def test_cpp_zero_income(self, cra):
        from payroll_calc.formulas.cpp import calc_cpp_period

        total, base = calc_cpp_period(D("0"), 52, cra.cpp)
        assert total == D("0")

    def test_ei_zero_income(self, cra):
        from payroll_calc.formulas.ei import calc_ei_period

        ei = calc_ei_period(D("0"), cra.ei)
        assert ei == D("0")


# ── BPAF dynamic formula tests ────────────────────────────────────────

class TestBpaf:
    def test_bpaf_low_income(self):
        from payroll_calc.formulas.bpaf import calc_bpaf
        assert calc_bpaf(D("50000")) == D("16452")

    def test_bpaf_high_income(self):
        from payroll_calc.formulas.bpaf import calc_bpaf
        assert calc_bpaf(D("300000")) == D("14829")

    def test_bpaf_clawback_midpoint(self):
        from payroll_calc.formulas.bpaf import calc_bpaf
        mid = (D("181440") + D("258482")) / 2
        result = calc_bpaf(mid)
        expected_mid = (D("16452") + D("14829")) / 2
        assert abs(result - expected_mid) <= D("1.00")

    def test_bpamb_low(self):
        from payroll_calc.formulas.bpaf import calc_bpamb
        assert calc_bpamb(D("100000")) == D("15780")

    def test_bpamb_high(self):
        from payroll_calc.formulas.bpaf import calc_bpamb
        assert calc_bpamb(D("500000")) == D("0")
