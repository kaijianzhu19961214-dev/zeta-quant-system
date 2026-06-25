from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = Field(default="quant-data-hub", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    clickhouse_http_url: str = Field(default="http://127.0.0.1:18123", alias="CLICKHOUSE_HTTP_URL")
    clickhouse_database: str = Field(default="quant_market", alias="CLICKHOUSE_DATABASE")
    clickhouse_user: str = Field(default="quant", alias="CLICKHOUSE_USER")
    clickhouse_password: str | None = Field(default=None, alias="CLICKHOUSE_PASSWORD")


@lru_cache
def get_settings() -> Settings:
    return Settings()

