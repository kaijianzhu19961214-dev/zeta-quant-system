from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = Field(default="quant-factor-validation", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    quant_data_hub_base_url: str = Field(
        default="http://quant_data_hub:8000",
        alias="QUANT_DATA_HUB_BASE_URL",
    )
    quant_data_api_token: str | None = Field(default=None, alias="QUANT_DATA_API_TOKEN")
    quant_data_hub_timeout_seconds: float = Field(default=15.0, alias="QUANT_DATA_HUB_TIMEOUT_SECONDS")
    validation_persistence_enabled: bool = Field(
        default=False,
        alias="VALIDATION_PERSISTENCE_ENABLED",
    )
    validation_database_url: str | None = Field(
        default=None,
        alias="VALIDATION_DATABASE_URL",
    )
    validation_database_echo: bool = Field(
        default=False,
        alias="VALIDATION_DATABASE_ECHO",
    )
    validation_object_store_endpoint: str | None = Field(
        default=None,
        alias="VALIDATION_OBJECT_STORE_ENDPOINT",
    )
    validation_object_store_access_key: str | None = Field(
        default=None,
        alias="VALIDATION_OBJECT_STORE_ACCESS_KEY",
    )
    validation_object_store_secret_key: str | None = Field(
        default=None,
        alias="VALIDATION_OBJECT_STORE_SECRET_KEY",
    )
    validation_object_store_bucket: str = Field(
        default="quant-factor-data",
        alias="VALIDATION_OBJECT_STORE_BUCKET",
    )
    validation_object_store_secure: bool = Field(
        default=False,
        alias="VALIDATION_OBJECT_STORE_SECURE",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
