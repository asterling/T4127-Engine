"""Tests for the CLI interface."""

import json
import subprocess
import sys

import pytest


def run_cli(*args):
    """Run the CLI and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        [sys.executable, "-m", "payroll_calc", *args],
        capture_output=True, text=True, timeout=30,
    )
    return result.returncode, result.stdout, result.stderr


# ── Basic calculation ────────────────────────────────────────────────


class TestCliBasicCalculation:
    def test_human_output_contains_all_fields(self):
        rc, out, _ = run_cli("calculate", "--gross", "1000", "--province", "ON", "--period", "52")
        assert rc == 0
        assert "Gross pay:" in out
        assert "Province:" in out
        assert "Federal tax:" in out
        assert "Provincial tax:" in out
        assert "CPP:" in out
        assert "EI:" in out
        assert "Total deductions:" in out
        assert "Net pay:" in out

    def test_human_output_exact_values(self):
        rc, out, _ = run_cli("calculate", "--gross", "1000", "--province", "ON", "--period", "52")
        assert rc == 0
        assert "81.61" in out   # federal
        assert "45.80" in out   # provincial
        assert "55.50" in out   # cpp
        assert "16.30" in out   # ei
        assert "199.21" in out  # total deductions
        assert "800.79" in out  # net pay

    def test_human_output_shows_province_and_period(self):
        rc, out, _ = run_cli("calculate", "--gross", "2000", "--province", "AB", "--period", "26")
        assert rc == 0
        assert "AB" in out
        assert "26pp" in out

    def test_json_output_all_keys(self):
        rc, out, _ = run_cli("calculate", "--gross", "1000", "--province", "ON", "--period", "52", "--json")
        assert rc == 0
        data = json.loads(out)
        expected_keys = {"federal_tax", "provincial_tax", "total_tax", "cpp", "cpp2", "ei", "total_deductions", "bonus_tax"}
        assert set(data.keys()) == expected_keys

    def test_json_output_exact_values(self):
        rc, out, _ = run_cli("calculate", "--gross", "1000", "--province", "ON", "--period", "52", "--json")
        assert rc == 0
        data = json.loads(out)
        assert data["federal_tax"] == "81.61"
        assert data["provincial_tax"] == "45.80"
        assert data["total_tax"] == "127.41"
        assert data["cpp"] == "55.50"
        assert data["cpp2"] == "0.00"
        assert data["ei"] == "16.30"
        assert data["total_deductions"] == "199.21"
        assert data["bonus_tax"] is None

    def test_json_is_valid_parseable(self):
        rc, out, _ = run_cli("calculate", "--gross", "5000", "--province", "BC", "--period", "12", "--json")
        assert rc == 0
        data = json.loads(out)  # would raise if invalid JSON
        for key in ["federal_tax", "provincial_tax", "cpp", "ei", "total_deductions"]:
            float(data[key])  # would raise if not numeric


# ── All provinces ────────────────────────────────────────────────────


class TestCliAllProvinces:
    @pytest.mark.parametrize("prov", ["AB", "BC", "MB", "NB", "NL", "NS", "NT", "NU", "ON", "PE", "SK", "YT"])
    def test_province_weekly(self, prov):
        rc, out, _ = run_cli("calculate", "--gross", "2000", "--province", prov, "--period", "52", "--json")
        assert rc == 0
        data = json.loads(out)
        assert float(data["total_deductions"]) > 0
        assert float(data["federal_tax"]) > 0
        assert float(data["provincial_tax"]) >= 0

    @pytest.mark.parametrize("prov", ["AB", "BC", "MB", "NB", "NL", "NS", "NT", "NU", "ON", "PE", "SK", "YT"])
    def test_province_monthly(self, prov):
        rc, out, _ = run_cli("calculate", "--gross", "8000", "--province", prov, "--period", "12", "--json")
        assert rc == 0
        data = json.loads(out)
        assert float(data["total_deductions"]) > 0

    def test_lowercase_province_accepted(self):
        rc, out, _ = run_cli("calculate", "--gross", "1000", "--province", "on", "--period", "52", "--json")
        assert rc == 0
        data = json.loads(out)
        assert data["federal_tax"] == "81.61"


# ── All pay periods ──────────────────────────────────────────────────


class TestCliAllPayPeriods:
    @pytest.mark.parametrize("period", ["52", "26", "24", "12"])
    def test_pay_period(self, period):
        rc, out, _ = run_cli("calculate", "--gross", "3000", "--province", "ON", "--period", period, "--json")
        assert rc == 0
        data = json.loads(out)
        assert float(data["total_deductions"]) > 0

    def test_monthly_higher_deductions_than_weekly(self):
        """Monthly $4000 = $48K/yr; weekly $1000 = $52K/yr. But per-period monthly deductions should be higher."""
        rc, out, _ = run_cli("calculate", "--gross", "4000", "--province", "ON", "--period", "12", "--json")
        monthly = json.loads(out)
        rc, out, _ = run_cli("calculate", "--gross", "1000", "--province", "ON", "--period", "52", "--json")
        weekly = json.loads(out)
        assert float(monthly["total_deductions"]) > float(weekly["total_deductions"])


# ── Deductions and inputs ────────────────────────────────────────────


class TestCliDeductions:
    def test_rpp_reduces_tax(self):
        rc, out, _ = run_cli("calculate", "--gross", "3200", "--province", "ON", "--period", "26", "--json")
        no_rpp = json.loads(out)
        rc, out, _ = run_cli("calculate", "--gross", "3200", "--province", "ON", "--period", "26", "--rpp", "200", "--json")
        with_rpp = json.loads(out)
        assert float(with_rpp["federal_tax"]) < float(no_rpp["federal_tax"])

    def test_union_dues_reduce_tax(self):
        rc, out, _ = run_cli("calculate", "--gross", "3200", "--province", "ON", "--period", "26", "--json")
        no_dues = json.loads(out)
        rc, out, _ = run_cli("calculate", "--gross", "3200", "--province", "ON", "--period", "26", "--union-dues", "50", "--json")
        with_dues = json.loads(out)
        assert float(with_dues["federal_tax"]) < float(no_dues["federal_tax"])

    def test_bonus_produces_bonus_tax(self):
        rc, out, _ = run_cli(
            "calculate", "--gross", "1000", "--province", "ON", "--period", "52",
            "--bonus", "5000", "--json",
        )
        assert rc == 0
        data = json.loads(out)
        assert data["bonus_tax"] is not None
        assert float(data["bonus_tax"]) > 0

    def test_no_bonus_has_null_bonus_tax(self):
        rc, out, _ = run_cli("calculate", "--gross", "1000", "--province", "ON", "--period", "52", "--json")
        data = json.loads(out)
        assert data["bonus_tax"] is None

    def test_bonus_shown_in_human_output(self):
        rc, out, _ = run_cli(
            "calculate", "--gross", "1000", "--province", "ON", "--period", "52",
            "--bonus", "5000",
        )
        assert rc == 0
        assert "Bonus tax:" in out


# ── Claim codes ──────────────────────────────────────────────────────


class TestCliClaimCodes:
    def test_cc0_higher_tax_than_cc1(self):
        rc, out, _ = run_cli("calculate", "--gross", "1000", "--province", "ON", "--period", "52",
                             "--fed-cc", "0", "--prov-cc", "0", "--json")
        cc0 = json.loads(out)
        rc, out, _ = run_cli("calculate", "--gross", "1000", "--province", "ON", "--period", "52", "--json")
        cc1 = json.loads(out)
        assert float(cc0["total_tax"]) > float(cc1["total_tax"])

    def test_cc10_lower_tax_than_cc1(self):
        rc, out, _ = run_cli("calculate", "--gross", "1500", "--province", "ON", "--period", "52",
                             "--fed-cc", "10", "--prov-cc", "10", "--json")
        cc10 = json.loads(out)
        rc, out, _ = run_cli("calculate", "--gross", "1500", "--province", "ON", "--period", "52", "--json")
        cc1 = json.loads(out)
        assert float(cc10["total_tax"]) < float(cc1["total_tax"])

    def test_claim_code_shown_in_human_output(self):
        rc, out, _ = run_cli("calculate", "--gross", "1000", "--province", "ON", "--period", "52",
                             "--fed-cc", "3", "--prov-cc", "5")
        assert "CC3/5" in out


# ── YTD tracking ─────────────────────────────────────────────────────


class TestCliYtdTracking:
    def test_ytd_cpp_reduces_cpp(self):
        rc, out, _ = run_cli("calculate", "--gross", "1000", "--province", "ON", "--period", "52",
                             "--ytd-cpp", "4200", "--json")
        data = json.loads(out)
        assert float(data["cpp"]) < 55.50  # max annual is $4,230.45

    def test_ytd_ei_reduces_ei(self):
        rc, out, _ = run_cli("calculate", "--gross", "1000", "--province", "ON", "--period", "52",
                             "--ytd-ei", "1120", "--json")
        data = json.loads(out)
        assert float(data["ei"]) < 16.30  # max annual is $1,123.07

    def test_ytd_cpp_at_max_zeroes_cpp(self):
        rc, out, _ = run_cli("calculate", "--gross", "1000", "--province", "ON", "--period", "52",
                             "--ytd-cpp", "4230.45", "--json")
        data = json.loads(out)
        assert float(data["cpp"]) == 0

    def test_ytd_ei_at_max_zeroes_ei(self):
        rc, out, _ = run_cli("calculate", "--gross", "1000", "--province", "ON", "--period", "52",
                             "--ytd-ei", "1123.07", "--json")
        data = json.loads(out)
        assert float(data["ei"]) == 0

    def test_no_ytd_gives_full_deductions(self):
        rc, out, _ = run_cli("calculate", "--gross", "1000", "--province", "ON", "--period", "52", "--json")
        data = json.loads(out)
        assert float(data["cpp"]) == 55.50
        assert float(data["ei"]) == 16.30


# ── Edge cases ───────────────────────────────────────────────────────


class TestCliEdgeCases:
    def test_low_income_zero_tax(self):
        rc, out, _ = run_cli("calculate", "--gross", "200", "--province", "ON", "--period", "52", "--json")
        assert rc == 0
        data = json.loads(out)
        assert float(data["total_tax"]) == 0

    def test_very_high_income(self):
        rc, out, _ = run_cli("calculate", "--gross", "20000", "--province", "ON", "--period", "12", "--json")
        assert rc == 0
        data = json.loads(out)
        assert float(data["total_deductions"]) > 0
        assert float(data["federal_tax"]) > 0

    def test_one_cent_gross(self):
        rc, out, _ = run_cli("calculate", "--gross", "0.01", "--province", "ON", "--period", "52", "--json")
        assert rc == 0
        data = json.loads(out)
        assert float(data["total_deductions"]) >= 0

    def test_decimal_precision_preserved(self):
        rc, out, _ = run_cli("calculate", "--gross", "1234.56", "--province", "ON", "--period", "52", "--json")
        assert rc == 0
        data = json.loads(out)
        # All values should have exactly 2 decimal places
        for key in ["federal_tax", "provincial_tax", "cpp", "ei", "total_deductions"]:
            assert "." in data[key]
            assert len(data[key].split(".")[1]) == 2


# ── Error handling ───────────────────────────────────────────────────


class TestCliErrors:
    def test_invalid_province(self):
        rc, _, err = run_cli("calculate", "--gross", "1000", "--province", "XX", "--period", "52")
        assert rc != 0
        assert "unknown province" in err.lower()

    def test_invalid_period(self):
        rc, _, err = run_cli("calculate", "--gross", "1000", "--province", "ON", "--period", "99")
        assert rc != 0
        assert "invalid pay period" in err.lower()

    def test_invalid_gross_letters(self):
        rc, _, err = run_cli("calculate", "--gross", "abc", "--province", "ON", "--period", "52")
        assert rc != 0
        assert "invalid gross" in err.lower()

    def test_invalid_gross_empty(self):
        rc, _, _ = run_cli("calculate", "--gross", "", "--province", "ON", "--period", "52")
        assert rc != 0

    def test_missing_gross(self):
        rc, _, _ = run_cli("calculate", "--province", "ON", "--period", "52")
        assert rc != 0

    def test_missing_province(self):
        rc, _, _ = run_cli("calculate", "--gross", "1000", "--period", "52")
        assert rc != 0

    def test_missing_period(self):
        rc, _, _ = run_cli("calculate", "--gross", "1000", "--province", "ON")
        assert rc != 0

    def test_unknown_command(self):
        rc, _, _ = run_cli("bogus")
        assert rc != 0


# ── Help and usage ───────────────────────────────────────────────────


class TestCliHelp:
    def test_no_args_shows_help(self):
        rc, out, _ = run_cli()
        assert rc == 0
        assert "calculate" in out
        assert "download" in out
        assert "compare" in out

    def test_calculate_help(self):
        rc, out, _ = run_cli("calculate", "--help")
        assert rc == 0
        assert "--gross" in out
        assert "--province" in out
        assert "--period" in out
        assert "--json" in out
        assert "--fed-cc" in out
        assert "--bonus" in out

    def test_download_help(self):
        rc, out, _ = run_cli("download", "--help")
        assert rc == 0
        assert "download" in out.lower()
