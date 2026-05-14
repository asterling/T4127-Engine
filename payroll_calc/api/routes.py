"""FastAPI route definitions."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from ..config import Province, PayPeriod
from ..data.schema import CraData
from ..models import DeductionRequest, DeductionResponse
from ..calculator import calculate
from ..tables.t4032_generator import generate_t4032_table

router = APIRouter()

# CRA data is injected at startup via app.state
_cra: CraData = None


def set_cra_data(cra: CraData):
    global _cra
    _cra = cra


@router.post("/calculate", response_model=DeductionResponse)
def calculate_deductions(req: DeductionRequest):
    """Calculate payroll deductions for a single pay period."""
    return calculate(req, _cra)


@router.get("/t4032/{province}/{pay_period}/{table_type}.csv")
def get_t4032_table(province: Province, pay_period: PayPeriod, table_type: str):
    """Generate a T4032-style tax deduction table as CSV.

    table_type: "federal" or "provincial"
    """
    if table_type not in ("federal", "provincial"):
        raise HTTPException(400, "table_type must be 'federal' or 'provincial'")

    csv_content = generate_t4032_table(province, pay_period, _cra, table_type)
    return PlainTextResponse(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=t4032-{province.value.lower()}-{pay_period.value}pp-{table_type}.csv"},
    )


@router.get("/provinces")
def list_provinces():
    """List supported provinces."""
    return [{"code": p.value, "name": p.name} for p in Province]


@router.get("/claim-codes/{jurisdiction}")
def get_claim_codes(jurisdiction: str):
    """Get claim code table for a jurisdiction.

    jurisdiction: "federal" or a province code (e.g., "ON")
    """
    if jurisdiction.lower() == "federal":
        codes = _cra.federal_claim_codes
    else:
        province_code = jurisdiction.upper()
        if province_code not in _cra.provincial_claim_codes:
            raise HTTPException(404, f"Unknown jurisdiction: {jurisdiction}")
        codes = _cra.provincial_claim_codes[province_code]

    return [
        {
            "code": cc.code,
            "tc": str(cc.tc),
            "k1": str(cc.k1),
        }
        for cc in codes
    ]
