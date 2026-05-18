"""Photo processing job persistence helpers."""

from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import AuditLog, Photo, PhotoProcessingJob, SlideDesign
from app.services.audit_logs import create_audit_log
from app.services.exif import ExtractedMetadata, extract_metadata
from app.services.fallback_slide_design import build_fallback_slide_design
from app.services.geocoding import GeocodingResult, GeocodingService
from app.services.images import generate_preview, generate_thumbnail
from app.services.photos import (
    PHOTO_STATUS_DESIGN_GENERATED,
    PHOTO_STATUS_EXIF_PARSED,
    PHOTO_STATUS_FAILED,
    PHOTO_STATUS_PREVIEW_GENERATED,
    PHOTO_STATUS_PROCESSING,
    PHOTO_STATUS_READY,
)
from app.services.slide_designs import (
    create_slide_design,
    get_latest_active_slide_design,
    get_latest_slide_design_version,
)
from app.services.storage import ObjectStorage
from app.schemas.photo import SlideDesignCreate

PHOTO_JOB_TYPE_PHOTO_INGEST = "photo_ingest"
PHOTO_JOB_TYPE_REVERSE_GEOCODE = "reverse_geocode"
PHOTO_JOB_TYPE_FALLBACK_REGENERATE = "fallback_regenerate"
PHOTO_JOB_TYPE_PHOTO_PURGE = "photo_purge"
PHOTO_JOB_TYPE_METADATA_THUMBNAIL = PHOTO_JOB_TYPE_PHOTO_INGEST
PHOTO_JOB_STATUS_PENDING = "pending"
PHOTO_JOB_STATUS_RUNNING = "running"
PHOTO_JOB_STATUS_SUCCEEDED = "succeeded"
PHOTO_JOB_STATUS_FAILED = "failed"

SUPPORTED_JOB_TYPES = (
    PHOTO_JOB_TYPE_PHOTO_INGEST,
    PHOTO_JOB_TYPE_REVERSE_GEOCODE,
    PHOTO_JOB_TYPE_FALLBACK_REGENERATE,
    PHOTO_JOB_TYPE_PHOTO_PURGE,
)


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
        .where(
            PhotoProcessingJob.photo_id == photo_id,
            PhotoProcessingJob.job_type.in_(SUPPORTED_JOB_TYPES),
        )
        .order_by(PhotoProcessingJob.created_at.desc(), PhotoProcessingJob.id.desc())
    )


def claim_next_pending_job(db: Session) -> PhotoProcessingJob | None:
    """Claim the oldest pending job for this worker."""

    job = db.scalar(
        select(PhotoProcessingJob)
        .where(
            PhotoProcessingJob.status == PHOTO_JOB_STATUS_PENDING,
            PhotoProcessingJob.attempts < PhotoProcessingJob.max_attempts,
            PhotoProcessingJob.job_type.in_(SUPPORTED_JOB_TYPES),
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


def mark_geocode_job_succeeded(
    db: Session,
    job: PhotoProcessingJob,
    photo: Photo,
    result: GeocodingResult,
    provider_name: str,
) -> None:
    """Write location fields and mark geocoding done. Photo status unchanged."""

    now = utc_now()
    photo.location_name = result.name
    photo.location_country = result.country
    photo.location_region = result.region
    photo.location_city = result.city
    photo.location_district = result.district
    photo.location_road = result.road
    photo.geocoding_status = "succeeded"
    photo.geocoding_provider = provider_name
    photo.geocoding_error = None
    photo.geocoded_at = now
    photo.updated_at = now
    job.status = PHOTO_JOB_STATUS_SUCCEEDED
    job.error_message = None
    job.finished_at = now
    job.updated_at = now
    db.add(photo)
    db.add(job)
    db.commit()


def mark_geocode_job_failed(
    db: Session,
    job: PhotoProcessingJob,
    photo: Photo | None,
    error_message: str,
) -> None:
    """Record geocoding failure. Photo status stays unchanged."""

    now = utc_now()
    if job.attempts >= job.max_attempts:
        job.status = PHOTO_JOB_STATUS_FAILED
        job.finished_at = now
        if photo is not None:
            photo.geocoding_status = "failed"
            photo.geocoding_error = error_message[:2000]
            photo.updated_at = now
            db.add(photo)
    else:
        job.status = PHOTO_JOB_STATUS_PENDING
        job.finished_at = None
    job.error_message = error_message[:2000]
    job.updated_at = now
    db.add(job)
    db.commit()


def create_reverse_geocode_job(
    db: Session,
    photo_id: str,
    *,
    max_attempts: int,
    provider_name: str,
) -> PhotoProcessingJob:
    """Enqueue a reverse-geocoding follow-on job after a successful ingest."""

    existing = _has_pending_or_running_job(db, photo_id, PHOTO_JOB_TYPE_REVERSE_GEOCODE)
    if existing is not None:
        return existing
    job = PhotoProcessingJob(
        photo_id=photo_id,
        job_type=PHOTO_JOB_TYPE_REVERSE_GEOCODE,
        status=PHOTO_JOB_STATUS_PENDING,
        attempts=0,
        max_attempts=max_attempts,
    )
    photo = db.get(Photo, photo_id)
    if photo is not None:
        photo.geocoding_status = "pending"
        photo.geocoding_provider = provider_name
        photo.updated_at = utc_now()
        db.add(photo)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def _has_pending_or_running_job(db: Session, photo_id: str, job_type: str) -> PhotoProcessingJob | None:
    """Return an existing pending/running job of the given type, or None."""

    return db.scalar(
        select(PhotoProcessingJob)
        .where(
            PhotoProcessingJob.photo_id == photo_id,
            PhotoProcessingJob.job_type == job_type,
            PhotoProcessingJob.status.in_([PHOTO_JOB_STATUS_PENDING, PHOTO_JOB_STATUS_RUNNING]),
        )
    )


def create_next_job(
    db: Session,
    photo_id: str,
    *,
    job_type: str,
    max_attempts: int,
) -> PhotoProcessingJob:
    """Enqueue a follow-on job with duplicate protection."""

    existing = _has_pending_or_running_job(db, photo_id, job_type)
    if existing is not None:
        return existing
    job = PhotoProcessingJob(
        photo_id=photo_id,
        job_type=job_type,
        status=PHOTO_JOB_STATUS_PENDING,
        attempts=0,
        max_attempts=max_attempts,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def create_fallback_regenerate_job(
    db: Session,
    photo_id: str,
    *,
    max_attempts: int,
) -> PhotoProcessingJob:
    return create_next_job(
        db,
        photo_id,
        job_type=PHOTO_JOB_TYPE_FALLBACK_REGENERATE,
        max_attempts=max_attempts,
    )


def create_photo_purge_job(
    db: Session,
    photo_id: str,
    *,
    max_attempts: int,
) -> PhotoProcessingJob:
    """Enqueue a photo_purge job with duplicate protection."""

    return create_next_job(
        db,
        photo_id,
        job_type=PHOTO_JOB_TYPE_PHOTO_PURGE,
        max_attempts=max_attempts,
    )


def _build_photo_delete_snapshot(photo: Photo) -> dict:
    return {
        "owner_id": photo.owner_id,
        "category": photo.category,
        "status": photo.status,
        "include_in_showcase": photo.include_in_showcase,
        "final_caption": photo.final_caption,
        "location_name": photo.location_name,
        "object_key_original": photo.object_key_original,
        "object_key_thumbnail": photo.object_key_thumbnail,
        "object_key_preview": photo.object_key_preview,
    }


def _get_delete_request_audit_context(
    db: Session,
    photo_id: str | None,
) -> tuple[str | None, dict | None]:
    if photo_id is None:
        return None, None

    log_entry = db.scalar(
        select(AuditLog)
        .where(
            AuditLog.action == "photo.delete_requested",
            AuditLog.target_type == "photo",
            AuditLog.target_id == photo_id,
        )
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
    )
    if log_entry is None:
        return None, None

    detail = log_entry.detail if isinstance(log_entry.detail, dict) else {}
    snapshot = detail.get("photo_snapshot") if isinstance(detail, dict) else None
    return log_entry.admin_id, snapshot if isinstance(snapshot, dict) else None


def _create_photo_delete_result_audit(
    db: Session,
    *,
    action: str,
    photo_id: str | None,
    job_id: str,
    summary: str,
    error_message: str | None = None,
    photo_snapshot: dict | None = None,
) -> None:
    admin_id, requested_snapshot = _get_delete_request_audit_context(db, photo_id)
    detail: dict = {
        "job_id": job_id,
        "summary": summary,
        "photo_snapshot": photo_snapshot or requested_snapshot,
    }
    if error_message is not None:
        detail["error_message"] = error_message

    create_audit_log(
        db,
        admin_id=admin_id,
        action=action,
        target_type="photo",
        target_id=photo_id,
        detail=detail,
    )


def _mark_photo_purge_job_succeeded(db: Session, job: PhotoProcessingJob) -> None:
    """Mark a purge job succeeded after the target photo has been removed."""

    now = utc_now()
    job.photo_id = None
    job.status = PHOTO_JOB_STATUS_SUCCEEDED
    job.error_message = None
    job.finished_at = now
    job.updated_at = now
    db.add(job)
    db.commit()


def _mark_photo_purge_job_failed(db: Session, job: PhotoProcessingJob, error_message: str) -> None:
    """Record a purge failure without mutating photo state."""

    now = utc_now()
    if job.attempts >= job.max_attempts:
        job.status = PHOTO_JOB_STATUS_FAILED
        job.finished_at = now
    else:
        job.status = PHOTO_JOB_STATUS_PENDING
        job.finished_at = None
    job.error_message = error_message[:2000]
    job.updated_at = now
    db.add(job)
    db.commit()


def process_photo_purge_job(
    db: Session,
    job: PhotoProcessingJob,
    photo: Photo | None,
    storage: ObjectStorage,
) -> bool:
    """Permanently delete photo objects and records while preserving the purge job row."""

    target_photo_id = photo.id if photo is not None else job.photo_id

    if photo is None:
        _mark_photo_purge_job_succeeded(db, job)
        _create_photo_delete_result_audit(
            db,
            action="photo.delete_succeeded",
            photo_id=target_photo_id,
            job_id=job.id,
            summary="Permanent photo deletion completed",
        )
        return True

    photo_snapshot = _build_photo_delete_snapshot(photo)
    try:
        object_keys = [
            photo.object_key_original,
            photo.object_key_preview,
            photo.object_key_thumbnail,
        ]
        for object_key in object_keys:
            if object_key:
                storage.delete_object(object_key)

        for design in db.scalars(select(SlideDesign).where(SlideDesign.photo_id == photo.id)).all():
            db.delete(design)

        for related_job in db.scalars(
            select(PhotoProcessingJob).where(
                PhotoProcessingJob.photo_id == photo.id,
                PhotoProcessingJob.id != job.id,
            )
        ).all():
            db.delete(related_job)

        job.photo_id = None
        db.add(job)
        db.delete(photo)
        db.commit()
    except Exception as exc:
        db.rollback()
        _mark_photo_purge_job_failed(db, job, str(exc))
        _create_photo_delete_result_audit(
            db,
            action="photo.delete_failed",
            photo_id=target_photo_id,
            job_id=job.id,
            summary="Permanent photo deletion failed",
            error_message=str(exc)[:2000],
            photo_snapshot=photo_snapshot,
        )
        return True

    _mark_photo_purge_job_succeeded(db, job)
    _create_photo_delete_result_audit(
        db,
        action="photo.delete_succeeded",
        photo_id=target_photo_id,
        job_id=job.id,
        summary="Permanent photo deletion completed",
        photo_snapshot=photo_snapshot,
    )
    return True


def _publish_new_active_design(
    db: Session,
    photo: Photo,
    job: PhotoProcessingJob,
    design_json: dict,
    *,
    source: str,
) -> None:
    active_design = get_latest_active_slide_design(db, photo.id)
    now = utc_now()
    if active_design is not None and active_design.status == "active":
        active_design.status = "draft"
        active_design.updated_at = now
        db.add(active_design)

    create_slide_design(
        db,
        photo.id,
        SlideDesignCreate(
            version=get_latest_slide_design_version(db, photo.id) + 1,
            design_json=design_json,
            source=source,
            status="active",
            validation_errors=None,
        ),
    )

    photo.updated_at = now
    job.status = PHOTO_JOB_STATUS_SUCCEEDED
    job.error_message = None
    job.finished_at = now
    job.updated_at = now
    db.add(photo)
    db.add(job)
    db.commit()


def process_fallback_regenerate_job(
    db: Session,
    job: PhotoProcessingJob,
    photo: Photo,
) -> bool:
    metadata = ExtractedMetadata(
        width=photo.width,
        height=photo.height,
        taken_at=photo.taken_at,
        gps_lat=photo.gps_lat,
        gps_lng=photo.gps_lng,
        camera_make=photo.camera_make,
        camera_model=photo.camera_model,
        exif_json=photo.exif_json,
    )
    design_json = build_fallback_slide_design(photo, metadata)
    _publish_new_active_design(db, photo, job, design_json, source="fallback")
    return True


def process_reverse_geocode_job(
    db: Session,
    job: PhotoProcessingJob,
    photo: Photo,
    geocoding: GeocodingService,
) -> bool:
    """Attempt reverse geocoding for a photo with GPS coordinates."""

    if not geocoding.enabled:
        mark_geocode_job_failed(db, job, photo, "Geocoding is disabled")
        return True
    if photo.gps_lat is None or photo.gps_lng is None:
        mark_geocode_job_failed(db, job, photo, "No GPS coordinates available")
        return True
    try:
        result = geocoding.reverse_geocode(photo.gps_lat, photo.gps_lng)
    except Exception as exc:
        mark_geocode_job_failed(db, job, photo, str(exc))
        return True
    if result is None:
        mark_geocode_job_failed(db, job, photo, "No geocoding results returned")
    else:
        mark_geocode_job_succeeded(db, job, photo, result, geocoding.provider_name)
    return True


def process_next_photo_job(
    db: Session,
    storage: ObjectStorage,
    *,
    thumbnail_size_px: int = 512,
    preview_max_size_px: int = 2048,
    geocoding: GeocodingService | None = None,
    geocoding_max_attempts: int = 2,
) -> bool:
    """Process one pending photo job if one is available."""

    job = claim_next_pending_job(db)
    if job is None:
        return False

    photo = db.get(Photo, job.photo_id)

    if job.job_type == PHOTO_JOB_TYPE_PHOTO_PURGE:
        return process_photo_purge_job(db, job, photo, storage)

    if job.job_type == PHOTO_JOB_TYPE_REVERSE_GEOCODE:
        if photo is None:
            mark_geocode_job_failed(db, job, None, "Photo not found")
            return True
        if geocoding is None:
            mark_geocode_job_failed(db, job, photo, "Geocoding service not available")
            return True
        return process_reverse_geocode_job(db, job, photo, geocoding)

    if job.job_type == PHOTO_JOB_TYPE_FALLBACK_REGENERATE:
        if photo is None:
            mark_job_failed(db, job, None, "Photo not found")
            return True
        return process_fallback_regenerate_job(db, job, photo)

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

    if (
        geocoding is not None
        and geocoding.enabled
        and metadata.gps_lat is not None
        and metadata.gps_lng is not None
    ):
        create_reverse_geocode_job(
            db,
            photo.id,
            max_attempts=geocoding_max_attempts,
            provider_name=geocoding.provider_name,
        )

    return True
