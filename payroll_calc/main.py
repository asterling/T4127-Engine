"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from .data.loader import load_cra_data
from .api.routes import router, set_cra_data


@asynccontextmanager
async def lifespan(app: FastAPI):
    cra = load_cra_data()
    set_cra_data(cra)
    yield


app = FastAPI(
    title="CRA Payroll Deductions Calculator",
    description="Canadian payroll deductions calculator implementing T4127 (122nd Edition, Jan 2026)",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(router)
