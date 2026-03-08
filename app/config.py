"""Application configuration for FastAPI runtime and service behavior."""

from __future__ import annotations

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


def _to_bool(value: str | None, default: bool = False) -> bool:
    """Parse environment truthy/falsey values."""
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _to_list(value: str | None, default: list[str] | None = None) -> list[str]:
    """Split comma-separated environment values into a normalized list."""
    if not value:
        return list(default or [])
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(slots=True)
class Settings:
    """Runtime settings loaded from environment variables."""

    app_env: str
    debug: bool
    secret_key: str
    log_level: str

    database_url: str
    sermon_storage_root: str

    allowed_hosts: list[str]
    cors_allowed_origins: list[str]
    cors_allow_credentials: bool

    cookie_secure: bool
    cookie_samesite: str
    session_cookie_name: str
    csrf_cookie_name: str

    session_ttl_minutes: int
    token_ttl_minutes: int

    bootstrap_admin_username: str | None
    bootstrap_admin_password: str | None

    @staticmethod
    def from_env() -> "Settings":
        """Construct settings from current process environment variables."""
        app_env = os.getenv("APP_ENV", "development").strip().lower()
        debug = _to_bool(os.getenv("APP_DEBUG"), default=(app_env != "production"))

        db_name = os.getenv("DB_NAME", "sermon_archive")
        db_user = os.getenv("DB_USER", "sermon_user")
        db_password = os.getenv("DB_PASSWORD", "")
        db_host = os.getenv("DB_HOST", "127.0.0.1")
        db_port = os.getenv("DB_PORT", "3306")
        default_db_url = (
            f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        )

        cookie_secure_default = app_env == "production"

        return Settings(
            app_env=app_env,
            debug=debug,
            secret_key=os.getenv(
                "APP_SECRET_KEY", os.getenv("DJANGO_SECRET_KEY", "dev-secret-key")
            ),
            log_level=os.getenv(
                "APP_LOG_LEVEL", os.getenv("DJANGO_LOG_LEVEL", "INFO")
            ).upper(),
            database_url=os.getenv("DATABASE_URL", default_db_url),
            sermon_storage_root=os.getenv("SERMON_STORAGE_ROOT", "."),
            allowed_hosts=_to_list(
                os.getenv(
                    "APP_ALLOWED_HOSTS",
                    os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1"),
                )
            ),
            cors_allowed_origins=_to_list(
                os.getenv(
                    "APP_CORS_ALLOWED_ORIGINS",
                    os.getenv("DJANGO_CORS_ALLOWED_ORIGINS", "http://localhost:3000"),
                )
            ),
            cors_allow_credentials=_to_bool(
                os.getenv("APP_CORS_ALLOW_CREDENTIALS"), default=True
            ),
            cookie_secure=_to_bool(
                os.getenv("APP_COOKIE_SECURE"), default=cookie_secure_default
            ),
            cookie_samesite=os.getenv("APP_COOKIE_SAMESITE", "lax").lower(),
            session_cookie_name=os.getenv("APP_SESSION_COOKIE_NAME", "sessionid"),
            csrf_cookie_name=os.getenv("APP_CSRF_COOKIE_NAME", "csrftoken"),
            session_ttl_minutes=int(os.getenv("APP_SESSION_TTL_MINUTES", "10080")),
            token_ttl_minutes=int(os.getenv("APP_TOKEN_TTL_MINUTES", "1440")),
            bootstrap_admin_username=os.getenv("APP_BOOTSTRAP_ADMIN_USERNAME"),
            bootstrap_admin_password=os.getenv("APP_BOOTSTRAP_ADMIN_PASSWORD"),
        )


settings = Settings.from_env()
