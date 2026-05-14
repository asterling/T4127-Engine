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


class TestCliCalculate:
    def test_basic_calculation(self):
        rc, out, _ = run_cli("calculate", "--gross", "1000", "--province", "ON", "--period", "52")
        assert rc == 0
        assert "Federal tax:" in out
        assert "81.61" in out
        assert "Net pay:" in out

    def test_json_output(self):
        rc, out, _ = run_cli("calculate", "--gross", "1000", "--province", "ON", "--period", "52", "--json")
        assert rc == 0
        data = json.loads(out)
        assert data["federal_tax"] == "81.61"
        assert data["provincial_tax"] == "45.80"
        assert data["cpp"] == "55.50"
        assert data["ei"] == "16.30"
        assert data["total_deductions"] == "199.21"

    def test_all_provinces(self):
        for prov in ["AB", "BC", "MB", "NB", "NL", "NS", "NT", "NU", "ON", "PE", "SK", "YT"]:
            rc, out, _ = run_cli("calculate", "--gross", "2000", "--province", prov, "--period", "26", "--json")
            assert rc == 0, f"Failed for {prov}"
            data = json.loads(out)
            assert float(data["total_deductions"]) > 0, f"Zero deductions for {prov}"

    def test_all_pay_periods(self):
        for period in ["52", "26", "24", "12"]:
            rc, out, _ = run_cli("calculate", "--gross", "3000", "--province", "ON", "--period", period, "--json")
            assert rc == 0, f"Failed for {period}pp"
            data = json.loads(out)
            assert float(data["total_deductions"]) > 0

    def test_with_deductions(self):
        rc, out, _ = run_cli(
            "calculate", "--gross", "3200", "--province", "MB", "--period", "26",
            "--rpp", "80", "--union-dues", "25", "--json",
        )
        assert rc == 0
        data = json.loads(out)
        assert float(data["total_deductions"]) > 0

    def test_with_bonus(self):
        rc, out, _ = run_cli(
            "calculate", "--gross", "1000", "--province", "ON", "--period", "52",
            "--bonus", "5000", "--json",
        )
        assert rc == 0
        data = json.loads(out)
        assert data["bonus_tax"] is not None
        assert float(data["bonus_tax"]) > 0

    def test_claim_code_0(self):
        rc, out, _ = run_cli(
            "calculate", "--gross", "1000", "--province", "ON", "--period", "52",
            "--fed-cc", "0", "--prov-cc", "0", "--json",
        )
        assert rc == 0
        data_cc0 = json.loads(out)

        rc, out, _ = run_cli(
            "calculate", "--gross", "1000", "--province", "ON", "--period", "52",
            "--json",
        )
        data_cc1 = json.loads(out)
        assert float(data_cc0["total_tax"]) > float(data_cc1["total_tax"])

    def test_ytd_tracking(self):
        rc, out, _ = run_cli(
            "calculate", "--gross", "1000", "--province", "ON", "--period", "52",
            "--ytd-cpp", "4200", "--ytd-ei", "1120", "--json",
        )
        assert rc == 0
        data = json.loads(out)
        # Near annual max — CPP/EI should be reduced
        assert float(data["cpp"]) < 55.50
        assert float(data["ei"]) < 16.30  # max is $1,123.07, YTD is $1,120


class TestCliErrors:
    def test_invalid_province(self):
        rc, _, err = run_cli("calculate", "--gross", "1000", "--province", "XX", "--period", "52")
        assert rc != 0
        assert "unknown province" in err.lower()

    def test_invalid_period(self):
        rc, _, err = run_cli("calculate", "--gross", "1000", "--province", "ON", "--period", "99")
        assert rc != 0
        assert "invalid pay period" in err.lower()

    def test_invalid_gross(self):
        rc, _, err = run_cli("calculate", "--gross", "abc", "--province", "ON", "--period", "52")
        assert rc != 0
        assert "invalid gross" in err.lower()

    def test_missing_args(self):
        rc, _, _ = run_cli("calculate")
        assert rc != 0


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
