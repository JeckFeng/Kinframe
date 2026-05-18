"""Helpers to enqueue missing geocoding follow-on jobs for existing photos."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Photo
from app.services.photo_jobs import (
    create_reverse_geocode_job,
)
from app.services.photos import PHOTO_STATUS_READY


def enqueue_missing_geocoding_jobs(
    db: Session,
    *,
    enabled: bool,
    max_attempts: int,
    provider_name: str,
) -> int:
    """Queue reverse geocoding for ready photos that have GPS but no successful location."""
    if not enabled:
        return 0

    photos = db.scalars(
        select(Photo).where(
            Photo.status == PHOTO_STATUS_READY,
            Photo.gps_lat.is_not(None),
            Photo.gps_lng.is_not(None),
            Photo.geocoding_status != "succeeded",
        )
    ).all()

    created = 0
    for photo in photos:
        create_reverse_geocode_job(
            db,
            photo.id,
            max_attempts=max_attempts,
            provider_name=provider_name,
        )
        created += 1
    return created
