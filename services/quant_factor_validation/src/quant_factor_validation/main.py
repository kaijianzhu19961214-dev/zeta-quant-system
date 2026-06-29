from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from quant_factor_validation.api.v1.dependencies import close_validation_database_engine
from quant_factor_validation.api.v1.health import router as health_router
from quant_factor_validation.api.v1.validation import router as validation_router
from quant_factor_validation.core.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    try:
        yield
    finally:
        await close_validation_database_engine()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.include_router(health_router)
    app.include_router(validation_router)
    return app


app = create_app()
