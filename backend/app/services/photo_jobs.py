"""Photo processing job persistence helpers."""

from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Photo, PhotoProcessingJob
from app.services.exif import ExtractedMetadata, extract_metadata
from app.services.fallback_slide_design import build_fallback_slide_design
from app.services.images import generate_preview, generate_thumbnail
from app.services.photos import (
    PHOTO_STATUS_DESIGN_GENERATED,
    PHOTO_STATUS_EXIF_PARSED,
    PHOTO_STATUS_FAILED,
    PHOTO_STATUS_PREVIEW_GENERATED,
    PHOTO_STATUS_PROCESSING,
    PHOTO_STATUS_READY,
)
from app.services.slide_designs import create_slide_design, get_latest_slide_design_version
from app.services.storage import ObjectStorage
from app.schemas.photo import SlideDesignCreate

PHOTO_JOB_TYPE_PHOTO_INGEST = "photo_ingest"
PHOTO_JOB_TYPE_SLIDE_DESIGN_GENERATE = "slide_design_generate"
PHOTO_JOB_TYPE_METADATA_THUMBNAIL = PHOTO_JOB_TYPE_PHOTO_INGEST
PHOTO_JOB_STATUS_PENDING = "pending"
PHOTO_JOB_STATUS_RUNNING = "running"
PHOTO_JOB_STATUS_SUCCEEDED = "succeeded"
PHOTO_JOB_STATUS_FAILED = "failed"


class PhotoJobCreateError(ValueError):
    """Raised when photo and processing job creation fails."""


def utc_now() -> datetime:
    """Return the current UTC timestamp."""

    return datetime.now(timezone.utc)


def create_photo_with_processing_job(
    db: Session,
    photo: Photo,
    *,
    max_attempts: int,
) -> tuple[Photo, PhotoProcessingJob]:
    """Persist a photo and its initial processing job atomically."""

    job = PhotoProcessingJob(
        photo_id=photo.id,
        job_type=PHOTO_JOB_TYPE_METADATA_THUMBNAIL,
        status=PHOTO_JOB_STATUS_PENDING,
        attempts=0,
        max_attempts=max_attempts,
    )
    db.add(photo)
    db.add(job)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise PhotoJobCreateError(photo.sha256) from exc
    db.refresh(photo)
    db.refresh(job)
    return photo, job


def get_latest_job_for_photo(db: Session, photo_id: str) -> PhotoProcessingJob | None:
    """Return the newest processing job for a photo."""

    return db.scalar(
        select(PhotoProcessingJob)
        .where(PhotoProcessingJob.photo_id == photo_id)
        .order_by(PhotoProcessingJob.created_at.desc(), PhotoProcessingJob.id.desc())
    )


def claim_next_pending_job(db: Session) -> PhotoProcessingJob | None:
    """Claim the oldest pending job for this worker."""

    job = db.scalar(
        select(PhotoProcessingJob)
        .where(
            PhotoProcessingJob.status == PHOTO_JOB_STATUS_PENDING,
            PhotoProcessingJob.attempts < PhotoProcessingJob.max_attempts,
        )
        .order_by(PhotoProcessingJob.created_at.asc(), PhotoProcessingJob.id.asc())
        .with_for_update(skip_locked=True)
    )
    if job is None:
        return None

    now = utc_now()
    job.status = PHOTO_JOB_STATUS_RUNNING
    job.attempts += 1
    job.started_at = now
    job.updated_at = now
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def mark_job_succeeded(
    db: Session,
    job: PhotoProcessingJob,
    photo: Photo,
    metadata: ExtractedMetadata,
) -> None:
    """Mark a job succeeded and publish processed photo metadata."""

    now = utc_now()
    photo.width = metadata.width
    photo.height = metadata.height
    photo.taken_at = metadata.taken_at
    photo.gps_lat = metadata.gps_lat
    photo.gps_lng = metadata.gps_lng
    photo.camera_make = metadata.camera_make
    photo.camera_model = metadata.camera_model
    photo.exif_json = metadata.exif_json
    photo.status = PHOTO_STATUS_READY
    photo.updated_at = now
    job.status = PHOTO_JOB_STATUS_SUCCEEDED
    job.error_message = None
    job.finished_at = now
    job.updated_at = now
    db.add(photo)
    db.add(job)
    db.commit()


def mark_job_failed(
    db: Session,
    job: PhotoProcessingJob,
    photo: Photo | None,
    error_message: str,
) -> None:
    """Record a processing failure and retry until attempts are exhausted."""

    now = utc_now()
    if job.attempts >= job.max_attempts:
        job.status = PHOTO_JOB_STATUS_FAILED
        job.finished_at = now
        if photo is not None:
            photo.status = PHOTO_STATUS_FAILED
            photo.updated_at = now
            db.add(photo)
    else:
        job.status = PHOTO_JOB_STATUS_PENDING
        job.finished_at = None
        if photo is not None:
            photo.status = PHOTO_STATUS_PROCESSING
            photo.updated_at = now
            db.add(photo)
    job.error_message = error_message[:2000]
    job.updated_at = now
    db.add(job)
    db.commit()


def process_next_photo_job(
    db: Session,
    storage: ObjectStorage,
    *,
    thumbnail_size_px: int = 512,
    preview_max_size_px: int = 2048,
) -> bool:
    """Process one pending photo job if one is available."""

    job = claim_next_pending_job(db)
    if job is None:
        return False

    photo = db.get(Photo, job.photo_id)
    try:
        if photo is None:
            raise RuntimeError(f"Photo does not exist: {job.photo_id}")
        original_bytes = storage.download_bytes(photo.object_key_original)
        suffix = Path(photo.object_key_original).suffix or ".jpg"
        metadata = extract_metadata(original_bytes, suffix, photo.uploaded_at)

        photo.status = PHOTO_STATUS_EXIF_PARSED
        photo.updated_at = utc_now()
        db.add(photo)
        db.commit()

        thumbnail_bytes = generate_thumbnail(original_bytes, max_size=thumbnail_size_px)
        preview_bytes = generate_preview(original_bytes, max_size=preview_max_size_px)
        storage.upload_bytes(photo.object_key_thumbnail, thumbnail_bytes, "image/webp")
        if photo.object_key_preview is not None:
            storage.upload_bytes(photo.object_key_preview, preview_bytes, "image/webp")

        photo.status = PHOTO_STATUS_PREVIEW_GENERATED
        photo.updated_at = utc_now()
        db.add(photo)
        db.commit()

        design_json = build_fallback_slide_design(photo, metadata)
        create_slide_design(
            db,
            photo.id,
            SlideDesignCreate(
                version=get_latest_slide_design_version(db, photo.id) + 1,
                design_json=design_json,
                source="fallback",
                status="active",
                validation_errors=None,
            ),
        )

        photo.status = PHOTO_STATUS_DESIGN_GENERATED
        photo.updated_at = utc_now()
        db.add(photo)
        db.commit()
    except Exception as exc:
        mark_job_failed(db, job, photo, str(exc))
        return True

    mark_job_succeeded(db, job, photo, metadata)
    return True
