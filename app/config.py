"""Application configuration for FastAPI."""

from typing import Literal
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    debug: bool = True
    log_level: str = "INFO"

    database_url: str = ''
    sermon_storage_root: str = "."

    cors_allowed_origins: list[str] | str = ["http://localhost:3000"]
    cors_allow_credentials: bool = True
    allowed_hosts: list[str] | str = ["localhost"]

    cookie_secure: bool = False
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"

    session_cookie_name: str = "sessionid"
    csrf_cookie_name: str = "csrftoken"

    session_ttl_minutes: int = 10080
    token_ttl_minutes: int = 1440

    @field_validator("cors_allowed_origins", "allowed_hosts", mode="before")
    @classmethod
    def parse_csv(cls, v):
        if isinstance(v, str):
            return [x.strip() for x in v.split(",") if x.strip()]
        return v


settings = Settings()
