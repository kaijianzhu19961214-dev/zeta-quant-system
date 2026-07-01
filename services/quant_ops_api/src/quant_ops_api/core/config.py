from functools import lru_cache

from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from quant_ops_api.schemas import ServiceEndpoint


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = Field(default="quant-ops-api", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    quant_data_hub_base_url: str = Field(
        default="http://quant_data_hub:8000",
        alias="QUANT_DATA_HUB_BASE_URL",
    )
    quant_factor_lab_base_url: str = Field(
        default="http://quant_factor_lab:8000",
        alias="QUANT_FACTOR_LAB_BASE_URL",
    )
    quant_factor_validation_base_url: str = Field(
        default="http://quant_factor_validation:8000",
        alias="QUANT_FACTOR_VALIDATION_BASE_URL",
    )
    artifact_ledger_database_url: str | None = Field(default=None, alias="ARTIFACT_LEDGER_DATABASE_URL")
    validation_database_url: str | None = Field(default=None, alias="VALIDATION_DATABASE_URL")
    artifact_ledger_database_schema: str | None = Field(default=None, alias="ARTIFACT_LEDGER_DATABASE_SCHEMA")
    validation_database_schema: str | None = Field(default=None, alias="VALIDATION_DATABASE_SCHEMA")
    artifact_ledger_query_limit: int = Field(default=20, ge=1, le=200, alias="ARTIFACT_LEDGER_QUERY_LIMIT")
    artifact_object_store_endpoint: str | None = Field(default=None, alias="ARTIFACT_OBJECT_STORE_ENDPOINT")
    validation_object_store_endpoint: str | None = Field(default=None, alias="VALIDATION_OBJECT_STORE_ENDPOINT")
    artifact_object_store_access_key: str | None = Field(default=None, alias="ARTIFACT_OBJECT_STORE_ACCESS_KEY")
    validation_object_store_access_key: str | None = Field(default=None, alias="VALIDATION_OBJECT_STORE_ACCESS_KEY")
    artifact_object_store_secret_key: str | None = Field(default=None, alias="ARTIFACT_OBJECT_STORE_SECRET_KEY")
    validation_object_store_secret_key: str | None = Field(default=None, alias="VALIDATION_OBJECT_STORE_SECRET_KEY")
    artifact_object_store_secure: bool | None = Field(default=None, alias="ARTIFACT_OBJECT_STORE_SECURE")
    validation_object_store_secure: bool | None = Field(default=None, alias="VALIDATION_OBJECT_STORE_SECURE")
    service_health_timeout_seconds: float = Field(default=5.0, alias="SERVICE_HEALTH_TIMEOUT_SECONDS")

    @field_validator("artifact_object_store_secure", "validation_object_store_secure", mode="before")
    @classmethod
    def normalize_blank_optional_bool(cls, value: Any) -> Any:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    def service_endpoints(self) -> list[ServiceEndpoint]:
        return [
            ServiceEndpoint(name="quant_data_hub", base_url=self.quant_data_hub_base_url),
            ServiceEndpoint(name="quant_factor_lab", base_url=self.quant_factor_lab_base_url),
            ServiceEndpoint(name="quant_factor_validation", base_url=self.quant_factor_validation_base_url),
        ]

    def artifact_ledger_read_database_url(self) -> str | None:
        for database_url in (self.artifact_ledger_database_url, self.validation_database_url):
            if database_url is not None and database_url.strip():
                return database_url.strip()
        return None

    def artifact_ledger_read_database_schema(self) -> str | None:
        for database_schema in (self.artifact_ledger_database_schema, self.validation_database_schema):
            if database_schema is not None and database_schema.strip():
                return database_schema.strip()
        return None

    def artifact_object_store_read_endpoint(self) -> str | None:
        return _read_first_stripped(
            values=[
                self.artifact_object_store_endpoint,
                self.validation_object_store_endpoint,
            ]
        )

    def artifact_object_store_read_access_key(self) -> str | None:
        return _read_first_stripped(
            values=[
                self.artifact_object_store_access_key,
                self.validation_object_store_access_key,
            ]
        )

    def artifact_object_store_read_secret_key(self) -> str | None:
        return _read_first_stripped(
            values=[
                self.artifact_object_store_secret_key,
                self.validation_object_store_secret_key,
            ]
        )

    def artifact_object_store_read_secure(self) -> bool:
        for is_secure in (self.artifact_object_store_secure, self.validation_object_store_secure):
            if is_secure is not None:
                return is_secure
        return False


def _read_first_stripped(*, values: list[str | None]) -> str | None:
    for value in values:
        if value is not None and value.strip():
            return value.strip()
    return None


@lru_cache
def get_settings() -> Settings:
    return Settings()
