"""Photo processing worker command."""

from __future__ import annotations

import argparse
import time
from collections.abc import Sequence

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.services.geocoding import create_geocoding_service
from app.services.photo_jobs import process_next_photo_job
from app.services.storage import MinioObjectStorage


def run_once() -> bool:
    """Process one pending photo job using configured services."""

    settings = get_settings()
    storage = MinioObjectStorage(settings)
    geocoding = create_geocoding_service(settings)
    with SessionLocal() as db:
        return process_next_photo_job(
            db,
            storage,
            thumbnail_size_px=settings.thumbnail_size_px,
            preview_max_size_px=settings.preview_max_size_px,
            geocoding=geocoding,
            geocoding_max_attempts=settings.geocoding_max_retries,
            ai_enabled=settings.ai_enabled,
            ai_max_attempts=settings.ai_max_retries + 1,
        )


def main(argv: Sequence[str] | None = None) -> int:
    """Run the photo processor once or as a polling loop."""

    settings = get_settings()
    parser = argparse.ArgumentParser(description="Process KinFrame photo jobs.")
    parser.add_argument("--once", action="store_true", help="process at most one pending job and exit")
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=settings.worker_poll_interval_seconds,
        help="seconds to wait between idle polling attempts",
    )
    args = parser.parse_args(argv)

    if not settings.worker_enabled:
        print("Photo worker is disabled by WORKER_ENABLED=0")
        return 0

    if args.once:
        processed = run_once()
        print("Processed one photo job" if processed else "No pending photo jobs")
        return 0

    print(f"Photo worker started; polling every {args.poll_interval}s")
    while True:
        processed = run_once()
        if not processed:
            time.sleep(args.poll_interval)


if __name__ == "__main__":
    raise SystemExit(main())
