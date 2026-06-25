from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


ServiceStatus = Literal["ok", "degraded", "down"]
OverviewStatus = Literal["ok", "degraded", "down"]


class ServiceEndpoint(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    base_url: str = Field(min_length=1, max_length=2048)
    health_path: str = Field(default="/health", min_length=1, max_length=256)


class ServiceHealth(BaseModel):
    name: str
    base_url: str
    status: ServiceStatus
    checked_at: datetime
    latency_ms: float | None = None
    http_status_code: int | None = None
    error_message: str | None = None


class OpsOverviewResponse(BaseModel):
    status: OverviewStatus
    generated_at: datetime
    services: list[ServiceHealth] = Field(default_factory=list)
    service_count: int = Field(ge=0)
    healthy_count: int = Field(ge=0)
    degraded_count: int = Field(ge=0)
    down_count: int = Field(ge=0)
