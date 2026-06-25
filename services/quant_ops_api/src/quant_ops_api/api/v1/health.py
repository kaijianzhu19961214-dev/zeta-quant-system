from fastapi import APIRouter
from pydantic import BaseModel

from quant_ops_api.core.config import get_settings

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    service: str


@router.get("/health", response_model=HealthResponse)
def read_health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(status="ok", service=settings.app_name)
