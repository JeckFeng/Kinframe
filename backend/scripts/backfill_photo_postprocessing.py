"""Enqueue missing geocoding and AI follow-on jobs for existing ready photos."""

from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.services.geocoding import create_geocoding_service
from app.services.photo_backfill import (
    enqueue_missing_ai_jobs,
    enqueue_missing_geocoding_jobs,
)


def main() -> int:
    settings = get_settings()
    geocoding = create_geocoding_service(settings)
    with SessionLocal() as db:
        geocoding_jobs = enqueue_missing_geocoding_jobs(
            db,
            enabled=geocoding.enabled,
            max_attempts=settings.geocoding_max_retries,
            provider_name=geocoding.provider_name,
        )
        ai_jobs = enqueue_missing_ai_jobs(
            db,
            enabled=settings.ai_enabled,
            max_attempts=settings.ai_max_retries + 1,
        )
    print(f"Enqueued {geocoding_jobs} geocoding job(s) and {ai_jobs} AI job(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
