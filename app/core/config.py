from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Order Management API"
    debug: bool = False
    postgres_db: str = "orders"
    postgres_user: str = "orders"
    postgres_password: SecretStr
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    jwt_secret: SecretStr = Field(min_length=32)
    jwt_algorithm: Literal["HS256"] = "HS256"
    jwt_access_token_expire_minutes: int = Field(default=60, ge=1, le=1440)
    currency_api_url: str = "https://api.frankfurter.dev/v2"
    currency_timeout_seconds: float = Field(default=5, gt=0, le=30)

    @property
    def database_url(self) -> URL:
        return URL.create(
            "postgresql+asyncpg",
            username=self.postgres_user,
            password=self.postgres_password.get_secret_value(),
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
