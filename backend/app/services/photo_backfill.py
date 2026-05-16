"""Helpers to enqueue missing geocoding and AI follow-on jobs for existing photos."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Photo
from app.services.photo_jobs import (
    create_reverse_geocode_job,
    create_vision_analyze_job,
)
from app.services.photos import PHOTO_STATUS_READY
from app.services.slide_designs import get_latest_active_slide_design


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


def enqueue_missing_ai_jobs(
    db: Session,
    *,
    enabled: bool,
    max_attempts: int,
) -> int:
    """Queue vision analysis for ready photos that still need AI analysis, caption, or design."""
    if not enabled:
        return 0

    photos = db.scalars(
        select(Photo).where(
            Photo.status == PHOTO_STATUS_READY,
            Photo.object_key_preview.is_not(None),
        )
    ).all()

    created = 0
    for photo in photos:
        active_design = get_latest_active_slide_design(db, photo.id)
        needs_ai_design = active_design is None or active_design.source == "fallback"
        needs_ai_caption = photo.ai_caption_enabled and not photo.user_message and not photo.ai_caption
        needs_ai_analysis = photo.ai_analysis_json is None
        if not (needs_ai_analysis or needs_ai_caption or needs_ai_design):
            continue
        create_vision_analyze_job(
            db,
            photo.id,
            max_attempts=max_attempts,
        )
        created += 1
    return created
