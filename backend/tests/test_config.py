"""Tests for v0.1 configuration fields."""

from app.core.config import Settings


def test_v01_settings_parse_from_environment_values() -> None:
    settings = Settings(
        backup_dir="data/backups",
        backup_include_env="1",
        worker_enabled="0",
        worker_poll_interval_seconds="7",
        photo_job_max_attempts="4",
        photo_job_retry_delay_seconds="45",
        thumbnail_size_px="640",
        preview_max_size_px="2560",
        heic_strategy="convert_if_available",
    )

    assert str(settings.backup_dir) == "data/backups"
    assert settings.backup_include_env is True
    assert settings.worker_enabled is False
    assert settings.worker_poll_interval_seconds == 7
    assert settings.photo_job_max_attempts == 4
    assert settings.photo_job_retry_delay_seconds == 45
    assert settings.thumbnail_size_px == 640
    assert settings.preview_max_size_px == 2560
    assert settings.heic_strategy == "convert_if_available"
