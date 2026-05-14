"""Main payroll deduction calculator — orchestrates all T4127 formula steps."""

from decimal import Decimal
from typing import Optional

from .config import Province, PayPeriod
from .data.schema import CraData
from .models import DeductionRequest, DeductionResponse
from .rounding import round_tax
from .formulas.cpp import calc_cpp_period, calc_cpp2_period, calc_f5, calc_f5a_f5b
from .formulas.ei import calc_ei_period
from .formulas.credits import (
    get_claim_code, calc_k1, calc_k2, calc_k4,
    calc_k1p, calc_k2p, calc_k4p_yukon, calc_k5p_alberta,
)
from .formulas.annual_income import calc_annual_taxable_income
from .formulas.federal_tax import calc_t3, calc_t1
from .formulas.provincial_tax import calc_t4, calc_t2
from .formulas.per_period_tax import calc_per_period_tax
from .formulas.bonus import calc_bonus_tax

ZERO = Decimal(0)


def calculate(req: DeductionRequest, cra: CraData) -> DeductionResponse:
    """Run the full T4127 Option 1 payroll deduction calculation."""

    P = req.pay_period.value
    province = req.province
    prov_params = cra.provinces[province.value]

    PI = req.pensionable_earnings if req.pensionable_earnings is not None else req.gross_pay
    IE = req.insurable_earnings if req.insurable_earnings is not None else req.gross_pay

    # ── CPP (Chapter 6) ──
    cpp_total, cpp_base_portion = calc_cpp_period(
        pi=PI, P=P, cpp=cra.cpp, D=req.ytd_cpp, PM=req.cpp_months,
    )
    cpp2 = calc_cpp2_period(
        pi=PI, P=P, cpp=cra.cpp, piytd=req.ytd_pensionable,
        D2=req.ytd_cpp2, PM=req.cpp_months,
    )

    # F5, F5A (additional CPP deduction from taxable income)
    F5 = calc_f5(cpp_total, cpp2, cra.cpp)
    F5A, F5B = calc_f5a_f5b(F5, PI, req.bonus)

    # ── EI (Chapter 7) ──
    ei = calc_ei_period(ie=IE, ei=cra.ei, D1=req.ytd_ei)

    # ── Step 1: Annual taxable income (A) ──
    A = calc_annual_taxable_income(
        P=P, I=req.gross_pay,
        F=req.rpp_contributions, F5A=F5A, U1=req.union_dues,
        HD=req.prescribed_zone, F1=req.annual_deductions,
    )

    # If A is negative, T = L
    if A < ZERO:
        return _zero_response(req, A, cpp_total, cpp_base_portion, cpp2, ei)

    # ── Step 2: Federal credits ──
    fed_cc = get_claim_code(cra.federal_claim_codes, req.federal_claim_code)
    K1 = calc_k1(fed_cc)
    K2 = calc_k2(cpp_total, ei, P, cra.cpp, cra.ei, PM=req.cpp_months)
    K4 = calc_k4(A, cra.federal.cea or Decimal("1501"))

    # ── Step 2: Basic federal tax (T3) ──
    T3 = calc_t3(A, cra.federal.brackets, K1, K2, K4=K4)

    # ── Step 3: Annual federal tax (T1) ──
    T1 = calc_t1(T3)

    # ── Step 4: Provincial credits ──
    prov_cc = get_claim_code(cra.provincial_claim_codes[province.value], req.provincial_claim_code)
    K1P = calc_k1p(prov_cc)
    lowest_prov_rate = prov_params.brackets[0].rate if prov_params.brackets else ZERO
    K2P = calc_k2p(cpp_total, ei, P, lowest_prov_rate, cra.cpp, cra.ei, PM=req.cpp_months)

    K4P = ZERO
    K5P = ZERO
    if province == Province.YT:
        K4P = calc_k4p_yukon(A, prov_params.cea or cra.federal.cea or Decimal("1501"))
    if province == Province.AB:
        K5P = calc_k5p_alberta(K1P, K2P)

    # ── Step 4: Basic provincial tax (T4) ──
    T4 = calc_t4(A, prov_params.brackets, K1P, K2P, K4P=K4P, K5P=K5P)

    # ── Step 5: Annual provincial tax (T2) ──
    # LCP (labour-sponsored funds credit) — requires employee input, default 0
    T2 = calc_t2(A, T4, province, prov_params, P=P, Y=req.dependants_for_reduction)

    # ── Step 6: Per-period tax ──
    T = calc_per_period_tax(T1, T2, P, L=req.additional_tax)

    # Split federal and provincial per-period amounts
    p = Decimal(P)
    fed_per_period = round_tax(T1 / p)
    prov_per_period = round_tax(T2 / p)

    # ── Bonus tax (if applicable) ──
    bonus_tax = None
    if req.bonus > ZERO:
        bonus_tax = _calc_bonus(req, cra, A, F5B)

    total_deductions = T + cpp_total + cpp2 + ei
    if bonus_tax is not None:
        total_deductions += bonus_tax

    return DeductionResponse(
        federal_tax=fed_per_period,
        provincial_tax=prov_per_period,
        total_tax=T,
        cpp_total=cpp_total,
        cpp_base_portion=round_tax(cpp_base_portion),
        cpp2=cpp2,
        ei_premium=ei,
        total_deductions=round_tax(total_deductions),
        bonus_tax=bonus_tax,
        annual_taxable_income=round_tax(A),
        basic_federal_tax=round_tax(T3),
        annual_federal_tax=round_tax(T1),
        basic_provincial_tax=round_tax(T4),
        annual_provincial_tax=round_tax(T2),
    )


def calculate_for_table(
    income: Decimal,
    P: int,
    province: Province,
    federal_claim_code: int,
    provincial_claim_code: int,
    cra: CraData,
) -> tuple[Decimal, Decimal]:
    """Simplified calculation for T4032 table generation.

    Returns (federal_tax_per_period, provincial_tax_per_period).

    For table generation:
    - No YTD tracking
    - No bonus
    - No additional deductions (F, F1, F2, U1, HD, L all zero)
    - CPP and EI computed at midpoint income for K2/K2P credits
    """
    PI = income
    IE = income
    cpp = cra.cpp
    ei_params = cra.ei
    prov_params = cra.provinces[province.value]

    # CPP and EI at this income level (for K2/K2P credit calculation)
    cpp_total, cpp_base = calc_cpp_period(pi=PI, P=P, cpp=cpp)
    cpp2 = calc_cpp2_period(pi=PI, P=P, cpp=cpp)
    F5 = calc_f5(cpp_total, cpp2, cpp)
    F5A = F5  # no bonus, so F5A = F5
    ei_amount = calc_ei_period(ie=IE, ei=ei_params)

    # Step 1: A (includes F5A — additional CPP deduction from taxable income)
    A = calc_annual_taxable_income(P=P, I=income, F5A=F5A)
    if A < ZERO:
        return ZERO, ZERO

    # Federal tax
    fed_cc = get_claim_code(cra.federal_claim_codes, federal_claim_code)
    K1 = calc_k1(fed_cc)
    K2 = calc_k2(cpp_total, ei_amount, P, cpp, ei_params)
    K4 = calc_k4(A, cra.federal.cea or Decimal("1501"))
    T3 = calc_t3(A, cra.federal.brackets, K1, K2, K4=K4)
    T1 = calc_t1(T3)

    # Provincial tax
    prov_cc = get_claim_code(cra.provincial_claim_codes[province.value], provincial_claim_code)
    K1P = calc_k1p(prov_cc)
    lowest_rate = prov_params.brackets[0].rate if prov_params.brackets else ZERO
    K2P = calc_k2p(cpp_total, ei_amount, P, lowest_rate, cpp, ei_params)

    K4P = ZERO
    K5P = ZERO
    if province == Province.YT:
        K4P = calc_k4p_yukon(A, prov_params.cea or cra.federal.cea or Decimal("1501"))
    if province == Province.AB:
        K5P = calc_k5p_alberta(K1P, K2P)

    T4 = calc_t4(A, prov_params.brackets, K1P, K2P, K4P=K4P, K5P=K5P)
    T2 = calc_t2(A, T4, province, prov_params, P=P)

    p = Decimal(P)
    fed_period = round_tax(T1 / p)
    prov_period = round_tax(T2 / p)

    return fed_period, prov_period


def _calc_bonus(req: DeductionRequest, cra: CraData, A_periodic: Decimal, F5B: Decimal) -> Decimal:
    """Calculate tax on bonus using the differential method."""
    P = req.pay_period.value
    province = req.province
    prov_params = cra.provinces[province.value]

    # A with bonus = A_periodic + (B - F3 - F5B)
    A_with = A_periodic + (req.bonus - F5B)
    A_without = A_periodic

    if A_with <= Decimal("5000"):
        return round_tax(Decimal("0.15") * req.bonus)

    # Federal
    fed_cc = get_claim_code(cra.federal_claim_codes, req.federal_claim_code)
    K1 = calc_k1(fed_cc)

    def _fed_t1(A):
        cpp_total, _ = calc_cpp_period(pi=req.gross_pay, P=P, cpp=cra.cpp)
        ei_amount = calc_ei_period(ie=req.gross_pay, ei=cra.ei)
        K2 = calc_k2(cpp_total, ei_amount, P, cra.cpp, cra.ei)
        K4 = calc_k4(A, cra.federal.cea or Decimal("1501"))
        T3 = calc_t3(A, cra.federal.brackets, K1, K2, K4=K4)
        return calc_t1(T3)

    # Provincial
    prov_cc = get_claim_code(cra.provincial_claim_codes[province.value], req.provincial_claim_code)
    K1P = calc_k1p(prov_cc)
    lowest_rate = prov_params.brackets[0].rate if prov_params.brackets else ZERO

    def _prov_t2(A):
        cpp_total, _ = calc_cpp_period(pi=req.gross_pay, P=P, cpp=cra.cpp)
        ei_amount = calc_ei_period(ie=req.gross_pay, ei=cra.ei)
        K2P = calc_k2p(cpp_total, ei_amount, P, lowest_rate, cra.cpp, cra.ei)
        K4P = ZERO
        K5P = ZERO
        if province == Province.YT:
            K4P = calc_k4p_yukon(A, prov_params.cea or cra.federal.cea or Decimal("1501"))
        if province == Province.AB:
            K5P = calc_k5p_alberta(K1P, K2P)
        T4 = calc_t4(A, prov_params.brackets, K1P, K2P, K4P=K4P, K5P=K5P)
        return calc_t2(A, T4, province, prov_params, P=P)

    t1_t2_with = _fed_t1(A_with) + _prov_t2(A_with)
    t1_t2_without = _fed_t1(A_without) + _prov_t2(A_without)

    return calc_bonus_tax(t1_t2_with, t1_t2_without)


def _zero_response(req, A, cpp_total, cpp_base, cpp2, ei):
    """Build a response when A is negative (only L applies)."""
    return DeductionResponse(
        federal_tax=req.additional_tax,
        provincial_tax=ZERO,
        total_tax=req.additional_tax,
        cpp_total=cpp_total,
        cpp_base_portion=cpp_base,
        cpp2=cpp2,
        ei_premium=ei,
        total_deductions=req.additional_tax + cpp_total + cpp2 + ei,
        annual_taxable_income=A,
        basic_federal_tax=ZERO,
        annual_federal_tax=ZERO,
        basic_provincial_tax=ZERO,
        annual_provincial_tax=ZERO,
    )
