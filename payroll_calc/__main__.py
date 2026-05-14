"""CLI entry point: python -m payroll_calc or t4127 command."""

import argparse
import sys
from decimal import Decimal, InvalidOperation


def main():
    parser = argparse.ArgumentParser(
        prog="t4127",
        description="Canadian payroll deductions calculator (CRA T4127 formulas)",
    )
    sub = parser.add_subparsers(dest="command")

    # ── calculate ────────────────────────────────────────────────────
    calc = sub.add_parser("calculate", help="Calculate payroll deductions for a single pay period")
    calc.add_argument("--gross", required=True, help="Gross pay for the period (e.g., 1000.00)")
    calc.add_argument("--province", required=True, help="Province code: AB, BC, MB, NB, NL, NS, NT, NU, ON, PE, SK, YT")
    calc.add_argument("--period", required=True, type=int, help="Pay periods per year: 52, 26, 24, or 12")
    calc.add_argument("--fed-cc", type=int, default=1, help="Federal claim code 0-10 (default: 1)")
    calc.add_argument("--prov-cc", type=int, default=1, help="Provincial claim code 0-10 (default: 1)")
    calc.add_argument("--bonus", default="0", help="Bonus amount (default: 0)")
    calc.add_argument("--rpp", default="0", help="RPP contributions per period (default: 0)")
    calc.add_argument("--union-dues", default="0", help="Union dues per period (default: 0)")
    calc.add_argument("--ytd-cpp", default="0", help="Year-to-date CPP contributions (default: 0)")
    calc.add_argument("--ytd-ei", default="0", help="Year-to-date EI premiums (default: 0)")
    calc.add_argument("--json", action="store_true", help="Output as JSON")

    # ── download ─────────────────────────────────────────────────────
    sub.add_parser("download", help="Download CRA rate data from canada.ca")

    # ── compare ──────────────────────────────────────────────────────
    cmp = sub.add_parser("compare", help="Compare against CRA's PDOC (requires Selenium + Chrome)")
    cmp.add_argument("gross", help="Gross pay")
    cmp.add_argument("province", help="Province code")
    cmp.add_argument("period", type=int, help="Pay periods per year")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    if args.command == "download":
        from .download_cra import download_all
        success = download_all()
        sys.exit(0 if success else 1)

    if args.command == "compare":
        from .pdoc_query import main as pdoc_main
        sys.argv = ["pdoc_query", "--compare", args.gross, args.province, str(args.period)]
        pdoc_main()
        return

    # ── calculate ────────────────────────────────────────────────────
    try:
        gross = Decimal(args.gross)
    except InvalidOperation:
        print(f"Error: invalid gross pay '{args.gross}'", file=sys.stderr)
        sys.exit(1)

    from .config import Province, PayPeriod
    from .models import DeductionRequest
    from .calculator import calculate
    from .data.loader import load_cra_data

    province_str = args.province.upper()
    try:
        province = Province(province_str)
    except ValueError:
        print(f"Error: unknown province '{province_str}'. Valid: {', '.join(p.value for p in Province)}", file=sys.stderr)
        sys.exit(1)

    try:
        pay_period = PayPeriod(args.period)
    except ValueError:
        print(f"Error: invalid pay period {args.period}. Valid: 52, 26, 24, 12", file=sys.stderr)
        sys.exit(1)

    cra = load_cra_data()

    req = DeductionRequest(
        province=province,
        pay_period=pay_period,
        gross_pay=gross,
        federal_claim_code=args.fed_cc,
        provincial_claim_code=args.prov_cc,
        bonus=Decimal(args.bonus),
        rpp_contributions=Decimal(args.rpp),
        union_dues=Decimal(args.union_dues),
        ytd_cpp=Decimal(args.ytd_cpp),
        ytd_ei=Decimal(args.ytd_ei),
    )

    result = calculate(req, cra)

    if args.json:
        import json
        print(json.dumps({
            "federal_tax": str(result.federal_tax),
            "provincial_tax": str(result.provincial_tax),
            "total_tax": str(result.total_tax),
            "cpp": str(result.cpp_total),
            "cpp2": str(result.cpp2),
            "ei": str(result.ei_premium),
            "total_deductions": str(result.total_deductions),
            "bonus_tax": str(result.bonus_tax) if result.bonus_tax else None,
        }, indent=2))
    else:
        print(f"  Gross pay:        ${gross:>12,.2f}")
        print(f"  Province:          {province_str} ({pay_period.value}pp, CC{args.fed_cc}/{args.prov_cc})")
        print()
        print(f"  Federal tax:      ${result.federal_tax:>12}")
        print(f"  Provincial tax:   ${result.provincial_tax:>12}")
        print(f"  CPP:              ${result.cpp_total:>12}")
        if result.cpp2 > 0:
            print(f"  CPP2:             ${result.cpp2:>12}")
        print(f"  EI:               ${result.ei_premium:>12}")
        if result.bonus_tax and result.bonus_tax > 0:
            print(f"  Bonus tax:        ${result.bonus_tax:>12}")
        print(f"                    {'─' * 13}")
        print(f"  Total deductions: ${result.total_deductions:>12}")
        print(f"  Net pay:          ${gross - result.total_deductions:>12,.2f}")


if __name__ == "__main__":
    main()
