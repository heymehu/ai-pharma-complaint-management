from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_ROOT.parent if (BACKEND_ROOT.parent / ".env").is_file() else BACKEND_ROOT


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / ".env", BACKEND_ROOT / ".env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "AIVOA Complaint Management System"
    app_version: str = "1.0.0"
    debug: bool = True
    api_prefix: str = "/api/v1"

    # SQLite for local; set DATABASE_URL for PostgreSQL in production
    database_url: str = "sqlite:///./aivoa.db"

    secret_key: str = "aivoa-dev-secret-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24

    google_api_key: str = ""
    ai_provider: str = "gemini"  # gemini | mock
    gemini_model: str = "gemini-2.5-flash"
    gemini_fallback_models: str = ""


    @property
    def gemini_model_chain(self) -> list[str]:
        models = [self.gemini_model]
        for m in self.gemini_fallback_models.split(","):
            m = m.strip()
            if m and m not in models:
                models.append(m)
        return models

    # Storage
    upload_dir: str = "./uploads"

    s3_endpoint: str = ""
    s3_bucket: str = "aivoa-attachments"
    s3_access_key: str = ""
    s3_secret_key: str = ""

    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


def clear_settings_cache() -> None:
    get_settings.cache_clear()
