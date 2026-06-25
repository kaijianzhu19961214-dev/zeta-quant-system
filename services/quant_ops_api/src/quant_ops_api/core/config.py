from functools import lru_cache

from pydantic import Field
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
    service_health_timeout_seconds: float = Field(default=5.0, alias="SERVICE_HEALTH_TIMEOUT_SECONDS")

    def service_endpoints(self) -> list[ServiceEndpoint]:
        return [
            ServiceEndpoint(name="quant_data_hub", base_url=self.quant_data_hub_base_url),
            ServiceEndpoint(name="quant_factor_lab", base_url=self.quant_factor_lab_base_url),
            ServiceEndpoint(name="quant_factor_validation", base_url=self.quant_factor_validation_base_url),
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
