"""Application configuration for FastAPI runtime and service behavior."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    debug: bool = Field(default=True, validation_alias="APP_DEBUG")
    log_level: str = Field(default="INFO", validation_alias="APP_LOG_LEVEL")
    database_url: str | None = Field(default=None, validation_alias="DATABASE_URL")
    sermon_storage_root: str = Field(
        default=".", validation_alias="SERMON_STORAGE_ROOT"
    )

    cors_allowed_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000"],
        validation_alias="APP_CORS_ALLOWED_ORIGINS",
    )
    cors_allow_credentials: bool = Field(
        default=True, validation_alias="APP_CORS_ALLOW_CREDENTIALS"
    )

    cookie_secure: bool = Field(default=False, validation_alias="APP_COOKIE_SECURE")
    cookie_samesite: Literal["lax", "strict", "none"] = Field(
        default="lax", validation_alias="APP_COOKIE_SAMESITE"
    )
    session_cookie_name: str = Field(
        default="sessionid", validation_alias="APP_SESSION_COOKIE_NAME"
    )
    csrf_cookie_name: str = Field(
        default="csrftoken", validation_alias="APP_CSRF_COOKIE_NAME"
    )

    session_ttl_minutes: int = Field(
        default=10080, validation_alias="APP_SESSION_TTL_MINUTES"
    )
    token_ttl_minutes: int = Field(
        default=1440, validation_alias="APP_TOKEN_TTL_MINUTES"
    )

    db_name: str = Field(default="sermon_archive", validation_alias="DB_NAME")
    db_user: str = Field(default="sermon_user", validation_alias="DB_USER")
    db_password: str = Field(default="", validation_alias="DB_PASSWORD")
    db_host: str = Field(default="127.0.0.1", validation_alias="DB_HOST")
    db_port: int = Field(default=3306, validation_alias="DB_PORT")

    @field_validator("log_level", mode="before")
    @classmethod
    def _normalize_log_level(cls, value: str) -> str:
        return value.upper()

    @field_validator("cookie_samesite", mode="before")
    @classmethod
    def _normalize_samesite(cls, value: str) -> str:
        return value.lower()

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def _parse_cors_allowed_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, list):
            return [item.strip() for item in value if item.strip()]
        return [item.strip() for item in value.split(",") if item.strip()]

    @model_validator(mode="after")
    def _build_database_url(self) -> "Settings":
        if self.database_url:
            return self
        self.database_url = (
            f"mysql+pymysql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )
        return self


settings = Settings()
