"""Application configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    """Runtime settings for the KinFrame backend."""

    app_env: str = "development"
    app_secret_key: str = "change-me"

    database_url: str = "postgresql+psycopg://kinframe:change-me@localhost:5432/kinframe"
    redis_url: str = "redis://localhost:6379/0"

    minio_endpoint: str = "localhost:9000"
    minio_public_endpoint: str | None = None
    minio_access_key: str = "kinframe"
    minio_secret_key: str = "change-me"
    minio_bucket: str = "kinframe-photos"
    minio_secure: bool = False

    max_upload_size_mb: int = Field(default=100, ge=1)
    allowed_image_types: list[str] = Field(
        default_factory=lambda: ["image/jpeg", "image/png", "image/webp"]
    )

    session_cookie_name: str = "kinframe_session"
    session_expire_days: int = Field(default=30, ge=1)

    backup_dir: Path = REPO_ROOT / "data" / "backups"
    backup_include_env: bool = False

    worker_enabled: bool = True
    worker_poll_interval_seconds: int = Field(default=5, ge=1)
    photo_job_max_attempts: int = Field(default=3, ge=1)
    photo_job_retry_delay_seconds: int = Field(default=30, ge=0)

    thumbnail_size_px: int = Field(default=512, ge=64)
    preview_max_size_px: int = Field(default=2048, ge=256)
    heic_strategy: Literal["reject", "convert_if_available"] = "reject"

    # Geocoding
    geocoding_enabled: bool = False
    geocoding_provider: Literal["nominatim", "amap", "noop"] = "nominatim"
    nominatim_endpoint: str = "https://nominatim.openstreetmap.org"
    amap_api_key: str | None = None
    geocoding_timeout_seconds: int = Field(default=30, ge=1)
    geocoding_max_retries: int = Field(default=2, ge=0)
    geocoding_rate_limit_per_second: float = Field(default=1.0, ge=0.1)

    # AI
    ai_enabled: bool = False
    ollama_endpoint: str | None = None
    ollama_vision_model: str | None = None
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_api_key: str | None = None
    deepseek_model: str | None = None
    ai_request_timeout_seconds: int = Field(default=500, ge=10)
    ai_max_retries: int = Field(default=1, ge=0)

    model_config = SettingsConfigDict(
        env_file=(REPO_ROOT / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("allowed_image_types", mode="before")
    @classmethod
    def _split_allowed_image_types(cls, value: Any) -> list[str] | Any:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("minio_endpoint", mode="before")
    @classmethod
    def _strip_minio_scheme(cls, value: Any) -> str | Any:
        if isinstance(value, str):
            return value.removeprefix("http://").removeprefix("https://")
        return value


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""

    return Settings()
