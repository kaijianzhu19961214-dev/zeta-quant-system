import base64
from typing import Any, Protocol

import httpx
from pydantic import Field
from quant_contracts.schemas.common import ContractModel


class ClickHouseConnectionSettings(ContractModel):
    http_url: str = Field(min_length=1)
    database: str = Field(min_length=1)
    user: str = Field(min_length=1)
    password: str | None = None


class ClickHouseReader(Protocol):
    async def query_json(self, query: str, *, timeout_seconds: int = 120) -> dict[str, Any]:
        raise NotImplementedError


def build_clickhouse_headers(settings: ClickHouseConnectionSettings) -> dict[str, str]:
    headers = {"Content-Type": "text/plain"}
    if settings.password is None:
        return headers

    token = f"{settings.user}:{settings.password}".encode("utf-8")
    headers["Authorization"] = f"Basic {base64.b64encode(token).decode('ascii')}"
    return headers


class ClickHouseHttpClient:
    def __init__(self, settings: ClickHouseConnectionSettings) -> None:
        self.settings = settings

    async def query_json(self, query: str, *, timeout_seconds: int = 120) -> dict[str, Any]:
        normalized_query = query.rstrip().rstrip(";")
        request_body = f"{normalized_query} FORMAT JSON"
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.post(
                self.settings.http_url.rstrip("/") + "/",
                content=request_body,
                headers=build_clickhouse_headers(self.settings),
            )

        if response.is_success:
            return response.json()

        raise RuntimeError(f"ClickHouse HTTP {response.status_code}: {response.text}")

