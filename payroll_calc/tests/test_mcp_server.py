"""Tests for MCP server tool functions and OpenAI schema."""

import json
from decimal import Decimal
from pathlib import Path

import pytest

from payroll_calc.mcp_server import (
    calculate_payroll_deductions,
    list_provinces,
    _serialize_response,
    PROVINCE_NAMES,
)


# ── calculate_payroll_deductions ─────────────────────────────────────


class TestCalculateBasic:
    def test_on_weekly_1000(self):
        result = calculate_payroll_deductions(gross_pay=1000, province="ON", pay_period=52)
        assert result["federal_tax"] == "81.61"
        assert result["provincial_tax"] == "45.80"
        assert result["cpp"] == "55.50"
        assert result["ei"] == "16.30"
        assert result["total_deductions"] == "199.21"

    def test_returns_all_expected_keys(self):
        result = calculate_payroll_deductions(gross_pay=1000, province="ON", pay_period=52)
        expected = {
            "federal_tax", "provincial_tax", "total_tax", "cpp", "cpp2", "ei",
            "total_deductions", "bonus_tax", "annual_taxable_income",
            "basic_federal_tax", "annual_federal_tax",
            "basic_provincial_tax", "annual_provincial_tax",
        }
        assert set(result.keys()) == expected

    def test_no_bonus_returns_null_bonus_tax(self):
        result = calculate_payroll_deductions(gross_pay=1000, province="ON", pay_period=52)
        assert result["bonus_tax"] is None

    def test_all_money_values_are_strings(self):
        result = calculate_payroll_deductions(gross_pay=1000, province="ON", pay_period=52)
        for key, val in result.items():
            if val is not None:
                assert isinstance(val, str), f"{key} should be str, got {type(val)}"

    def test_decimal_precision_two_places(self):
        result = calculate_payroll_deductions(gross_pay=1234.56, province="ON", pay_period=52)
        for key, val in result.items():
            if val is not None:
                assert "." in val, f"{key} missing decimal point"
                assert len(val.split(".")[1]) == 2, f"{key} should have 2 decimal places: {val}"


class TestCalculateAllProvinces:
    @pytest.mark.parametrize("prov", ["AB", "BC", "MB", "NB", "NL", "NS", "NT", "NU", "ON", "PE", "SK", "YT"])
    def test_province_returns_deductions(self, prov):
        result = calculate_payroll_deductions(gross_pay=2000, province=prov, pay_period=52)
        assert "error" not in result
        assert float(result["total_deductions"]) > 0
        assert float(result["federal_tax"]) > 0

    @pytest.mark.parametrize("prov", ["AB", "BC", "MB", "NB", "NL", "NS", "NT", "NU", "ON", "PE", "SK", "YT"])
    def test_province_monthly(self, prov):
        result = calculate_payroll_deductions(gross_pay=8000, province=prov, pay_period=12)
        assert "error" not in result
        assert float(result["total_deductions"]) > 0


class TestCalculateAllPeriods:
    @pytest.mark.parametrize("period", [52, 26, 24, 12])
    def test_pay_period(self, period):
        result = calculate_payroll_deductions(gross_pay=3000, province="ON", pay_period=period)
        assert "error" not in result
        assert float(result["total_deductions"]) > 0

    def test_monthly_higher_per_period_than_weekly(self):
        monthly = calculate_payroll_deductions(gross_pay=4000, province="ON", pay_period=12)
        weekly = calculate_payroll_deductions(gross_pay=1000, province="ON", pay_period=52)
        assert float(monthly["total_deductions"]) > float(weekly["total_deductions"])


class TestCalculateDeductions:
    def test_rpp_reduces_tax(self):
        without = calculate_payroll_deductions(gross_pay=3200, province="ON", pay_period=26)
        with_rpp = calculate_payroll_deductions(gross_pay=3200, province="ON", pay_period=26, rpp_contributions=200)
        assert float(with_rpp["federal_tax"]) < float(without["federal_tax"])

    def test_union_dues_reduce_tax(self):
        without = calculate_payroll_deductions(gross_pay=3200, province="ON", pay_period=26)
        with_dues = calculate_payroll_deductions(gross_pay=3200, province="ON", pay_period=26, union_dues=50)
        assert float(with_dues["federal_tax"]) < float(without["federal_tax"])

    def test_bonus_produces_bonus_tax(self):
        result = calculate_payroll_deductions(gross_pay=1000, province="ON", pay_period=52, bonus=5000)
        assert result["bonus_tax"] is not None
        assert float(result["bonus_tax"]) > 0

    def test_additional_tax_increases_total(self):
        without = calculate_payroll_deductions(gross_pay=1000, province="ON", pay_period=52)
        with_extra = calculate_payroll_deductions(gross_pay=1000, province="ON", pay_period=52, additional_tax=50)
        assert float(with_extra["total_deductions"]) > float(without["total_deductions"])


class TestCalculateClaimCodes:
    def test_cc0_higher_than_cc1(self):
        cc0 = calculate_payroll_deductions(gross_pay=1000, province="ON", pay_period=52,
                                           federal_claim_code=0, provincial_claim_code=0)
        cc1 = calculate_payroll_deductions(gross_pay=1000, province="ON", pay_period=52)
        assert float(cc0["total_tax"]) > float(cc1["total_tax"])

    def test_cc10_lower_than_cc1(self):
        cc10 = calculate_payroll_deductions(gross_pay=1500, province="ON", pay_period=52,
                                            federal_claim_code=10, provincial_claim_code=10)
        cc1 = calculate_payroll_deductions(gross_pay=1500, province="ON", pay_period=52)
        assert float(cc10["total_tax"]) < float(cc1["total_tax"])

    def test_claim_code_monotonic(self):
        """Higher claim codes should never produce more tax."""
        taxes = []
        for cc in range(0, 11):
            result = calculate_payroll_deductions(gross_pay=1500, province="ON", pay_period=52,
                                                  federal_claim_code=cc, provincial_claim_code=cc)
            taxes.append(float(result["total_tax"]))
        for i in range(len(taxes) - 1):
            assert taxes[i] >= taxes[i + 1], f"CC{i} tax {taxes[i]} < CC{i+1} tax {taxes[i+1]}"


class TestCalculateYtd:
    def test_ytd_cpp_reduces_cpp(self):
        result = calculate_payroll_deductions(gross_pay=1000, province="ON", pay_period=52, ytd_cpp=4200)
        assert float(result["cpp"]) < 55.50

    def test_ytd_ei_reduces_ei(self):
        result = calculate_payroll_deductions(gross_pay=1000, province="ON", pay_period=52, ytd_ei=1120)
        assert float(result["ei"]) < 16.30

    def test_cpp_at_max_zeroes(self):
        result = calculate_payroll_deductions(gross_pay=1000, province="ON", pay_period=52, ytd_cpp=4230.45)
        assert float(result["cpp"]) == 0

    def test_ei_at_max_zeroes(self):
        result = calculate_payroll_deductions(gross_pay=1000, province="ON", pay_period=52, ytd_ei=1123.07)
        assert float(result["ei"]) == 0


class TestCalculateEdgeCases:
    def test_low_income_zero_tax(self):
        result = calculate_payroll_deductions(gross_pay=200, province="ON", pay_period=52)
        assert float(result["total_tax"]) == 0

    def test_very_high_income(self):
        result = calculate_payroll_deductions(gross_pay=20000, province="ON", pay_period=12)
        assert float(result["total_deductions"]) > 0

    def test_one_cent(self):
        result = calculate_payroll_deductions(gross_pay=0.01, province="ON", pay_period=52)
        assert "error" not in result

    def test_lowercase_province(self):
        result = calculate_payroll_deductions(gross_pay=1000, province="on", pay_period=52)
        assert result["federal_tax"] == "81.61"

    def test_mixed_case_province(self):
        result = calculate_payroll_deductions(gross_pay=1000, province="On", pay_period=52)
        assert result["federal_tax"] == "81.61"


class TestCalculateErrors:
    def test_invalid_province(self):
        result = calculate_payroll_deductions(gross_pay=1000, province="XX", pay_period=52)
        assert "error" in result
        assert "Unknown province" in result["error"]

    def test_invalid_period(self):
        result = calculate_payroll_deductions(gross_pay=1000, province="ON", pay_period=99)
        assert "error" in result
        assert "Invalid pay period" in result["error"]

    def test_quebec_not_supported(self):
        result = calculate_payroll_deductions(gross_pay=1000, province="QC", pay_period=52)
        assert "error" in result


# ── list_provinces ───────────────────────────────────────────────────


class TestListProvinces:
    def test_returns_12_provinces(self):
        result = list_provinces()
        assert len(result) == 12

    def test_each_has_code_and_name(self):
        for p in list_provinces():
            assert "code" in p
            assert "name" in p
            assert len(p["code"]) == 2
            assert len(p["name"]) > 2

    def test_contains_ontario(self):
        codes = [p["code"] for p in list_provinces()]
        assert "ON" in codes

    def test_excludes_quebec(self):
        codes = [p["code"] for p in list_provinces()]
        assert "QC" not in codes

    def test_all_province_enum_values_present(self):
        from payroll_calc.config import Province
        result_codes = {p["code"] for p in list_provinces()}
        enum_codes = {p.value for p in Province}
        assert result_codes == enum_codes

    def test_names_match_mapping(self):
        for p in list_provinces():
            assert p["name"] == PROVINCE_NAMES[p["code"]]


# ── OpenAI tool schema ──────────────────────────────────────────────


SCHEMA_PATH = Path(__file__).parent.parent / "schemas" / "openai_tool.json"


class TestOpenAiSchema:
    @pytest.fixture
    def schema(self):
        with open(SCHEMA_PATH) as f:
            return json.load(f)

    def test_schema_is_valid_json(self):
        with open(SCHEMA_PATH) as f:
            json.load(f)  # would raise on invalid JSON

    def test_schema_is_list_of_two_tools(self, schema):
        assert isinstance(schema, list)
        assert len(schema) == 2

    def test_calculate_tool_structure(self, schema):
        calc = schema[0]
        assert calc["type"] == "function"
        assert calc["function"]["name"] == "calculate_payroll_deductions"
        assert "parameters" in calc["function"]
        assert "description" in calc["function"]

    def test_list_provinces_tool_structure(self, schema):
        lp = schema[1]
        assert lp["type"] == "function"
        assert lp["function"]["name"] == "list_provinces"

    def test_required_params(self, schema):
        params = schema[0]["function"]["parameters"]
        assert set(params["required"]) == {"gross_pay", "province", "pay_period"}

    def test_province_enum_values(self, schema):
        props = schema[0]["function"]["parameters"]["properties"]
        assert set(props["province"]["enum"]) == {"AB", "BC", "MB", "NB", "NL", "NS", "NT", "NU", "ON", "PE", "SK", "YT"}

    def test_pay_period_enum_values(self, schema):
        props = schema[0]["function"]["parameters"]["properties"]
        assert set(props["pay_period"]["enum"]) == {52, 26, 24, 12}

    def test_all_optional_params_have_defaults(self, schema):
        params = schema[0]["function"]["parameters"]
        props = params["properties"]
        required = set(params["required"])
        for name, prop in props.items():
            if name not in required:
                assert "default" in prop, f"Optional param '{name}' missing default"

    def test_schema_params_match_mcp_tool(self, schema):
        """Verify the OpenAI schema parameter names match the MCP tool function."""
        schema_params = set(schema[0]["function"]["parameters"]["properties"].keys())
        # Get the MCP tool function parameter names (skip 'self' if present)
        import inspect
        sig = inspect.signature(calculate_payroll_deductions)
        func_params = set(sig.parameters.keys())
        assert schema_params == func_params, f"Mismatch: schema={schema_params - func_params}, func={func_params - schema_params}"

    def test_no_additional_properties(self, schema):
        params = schema[0]["function"]["parameters"]
        assert params.get("additionalProperties") is False
