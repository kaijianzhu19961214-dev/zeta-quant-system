from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from quant_ops_api.api.v1.artifacts import router as artifacts_router
from quant_ops_api.api.v1.dependencies import dispose_validation_ledger_engine
from quant_ops_api.api.v1.factor_lab import router as factor_lab_router
from quant_ops_api.api.v1.factor_validation import router as factor_validation_router
from quant_ops_api.api.v1.health import router as health_router
from quant_ops_api.api.v1.overview import router as overview_router
from quant_ops_api.core.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    try:
        yield
    finally:
        await dispose_validation_ledger_engine()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.include_router(health_router)
    app.include_router(overview_router)
    app.include_router(factor_lab_router)
    app.include_router(factor_validation_router)
    app.include_router(artifacts_router)
    return app


app = create_app()
