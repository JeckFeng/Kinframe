"""Enqueue missing geocoding follow-on jobs for existing ready photos."""

from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.services.geocoding import create_geocoding_service
from app.services.photo_backfill import (
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
    print(f"Enqueued {geocoding_jobs} geocoding job(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
