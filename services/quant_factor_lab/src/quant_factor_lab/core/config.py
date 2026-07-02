from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = Field(default="quant-factor-lab", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    quant_data_hub_base_url: str = Field(
        default="http://quant_data_hub:8000",
        alias="QUANT_DATA_HUB_BASE_URL",
    )
    quant_data_api_token: str | None = Field(default=None, alias="QUANT_DATA_API_TOKEN")
    quant_data_hub_timeout_seconds: float = Field(default=15.0, alias="QUANT_DATA_HUB_TIMEOUT_SECONDS")
    algorithm_review_persistence_enabled: bool = Field(
        default=False,
        alias="ALGORITHM_REVIEW_PERSISTENCE_ENABLED",
    )
    algorithm_review_database_url: str | None = Field(default=None, alias="ALGORITHM_REVIEW_DATABASE_URL")
    algorithm_review_database_echo: bool = Field(default=False, alias="ALGORITHM_REVIEW_DATABASE_ECHO")
    algorithm_review_database_schema: str | None = Field(default=None, alias="ALGORITHM_REVIEW_DATABASE_SCHEMA")
    algorithm_review_create_schema: bool = Field(default=False, alias="ALGORITHM_REVIEW_CREATE_SCHEMA")


@lru_cache
def get_settings() -> Settings:
    return Settings()
