from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from quant_factor_lab.api.v1.dependencies import (
    close_algorithm_review_database_engine,
    initialize_algorithm_review_storage,
)
from quant_factor_lab.api.v1.factors import router as factors_router
from quant_factor_lab.api.v1.health import router as health_router
from quant_factor_lab.core.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await initialize_algorithm_review_storage()
    try:
        yield
    finally:
        await close_algorithm_review_database_engine()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.include_router(health_router)
    app.include_router(factors_router)
    return app


app = create_app()
