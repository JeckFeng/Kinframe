"""Photo upload and metadata API routes."""

from datetime import datetime, timezone
from pathlib import Path
import hashlib
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status

from app.api.deps import AppSettings, DbSession, get_current_user, get_object_storage
from app.models import Photo, User
from app.schemas.photo import (
    PhotoBatchUploadItem,
    PhotoBatchUploadResponse,
    PhotoCategoryRead,
    PhotoMessageUpdate,
    PhotoProcessingStatusResponse,
    PhotoRead,
    PhotoUpdate,
    PresignedUrlResponse,
    SlideDesignCreate,
    SlideDesignRead,
)
from app.services.photos import (
    PHOTO_STATUS_PROCESSING,
    PhotoPermissionError,
    can_modify_photo,
    delete_photo,
    get_photo,
    get_photo_by_sha256,
    list_photos,
    update_photo,
    update_user_message,
)
from app.services.photo_jobs import PhotoJobCreateError, create_photo_with_processing_job, get_latest_job_for_photo
from app.services.categories import get_valid_category_slugs, list_active_categories
from app.services.images import heic_conversion_available
from app.services.slide_designs import (
    DuplicateSlideDesignVersionError,
    create_slide_design,
    get_latest_active_slide_design,
)
from app.services.storage import ObjectStorage
from app.services.audit_logs import create_audit_log

router = APIRouter(prefix="/api/photos", tags=["photos"])

HEIC_MIME_TYPES = {"image/heic", "image/heif"}
BATCH_UPLOAD_MAX_FILES = 10
EXTENSIONS_BY_MIME_TYPE = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/heic": ".heic",
    "image/heif": ".heif",
}


FALLBACK_CATEGORY = "life"


def _validate_category(category: str | None, db: DbSession) -> str:
    if not category:
        return FALLBACK_CATEGORY
    valid_slugs = get_valid_category_slugs(db)
    if category not in valid_slugs:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Category must be one of: {', '.join(sorted(valid_slugs))}",
        )
    return category


def _extension_for_upload(file: UploadFile) -> str:
    if file.content_type in EXTENSIONS_BY_MIME_TYPE:
        return EXTENSIONS_BY_MIME_TYPE[file.content_type]
    suffix = Path(file.filename or "").suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".webp"}:
        return ".jpg" if suffix == ".jpeg" else suffix
    return ".bin"


def _object_keys(photo_id: str, extension: str, uploaded_at: datetime) -> tuple[str, str, str]:
    year = f"{uploaded_at.year:04d}"
    month = f"{uploaded_at.month:02d}"
    original_key = f"originals/{year}/{month}/{photo_id}{extension}"
    thumbnail_key = f"thumbnails/{year}/{month}/{photo_id}_512.webp"
    preview_key = f"previews/{year}/{month}/{photo_id}.webp"
    return original_key, thumbnail_key, preview_key


def _photo_or_404(db: DbSession, photo_id: str) -> Photo:
    photo = get_photo(db, photo_id)
    if photo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found")
    return photo


class UploadPhotoError(ValueError):
    """Internal upload validation error."""

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


async def _upload_one_photo(
    db: DbSession,
    settings: AppSettings,
    current_user: User,
    storage: ObjectStorage,
    file: UploadFile,
    *,
    category: str,
    category_provided: bool,
    user_message: str | None,
    ai_caption_enabled: bool,
    ai_category_enabled: bool,
    include_in_showcase: bool,
) -> PhotoRead:
    content_type = file.content_type or "application/octet-stream"
    if content_type in HEIC_MIME_TYPES:
        if settings.heic_strategy != "convert_if_available" or not heic_conversion_available():
            raise UploadPhotoError(
                status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                "HEIC/HEIF conversion is not available",
            )
    elif content_type not in settings.allowed_image_types:
        raise UploadPhotoError(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Unsupported image MIME type")

    max_size = settings.max_upload_size_mb * 1024 * 1024
    image_bytes = await file.read(max_size + 1)
    if not image_bytes:
        raise UploadPhotoError(status.HTTP_400_BAD_REQUEST, "Empty upload")
    if len(image_bytes) > max_size:
        raise UploadPhotoError(status.HTTP_413_CONTENT_TOO_LARGE, "File too large")

    sha256 = hashlib.sha256(image_bytes).hexdigest()
    if get_photo_by_sha256(db, sha256) is not None:
        raise UploadPhotoError(status.HTTP_409_CONFLICT, "Duplicate photo")

    uploaded_at = datetime.now(timezone.utc)
    extension = _extension_for_upload(file)
    photo_id = str(uuid4())
    original_key, thumbnail_key, preview_key = _object_keys(photo_id, extension, uploaded_at)

    try:
        storage.ensure_bucket()
        storage.upload_bytes(original_key, image_bytes, content_type)
    except Exception as exc:
        raise UploadPhotoError(status.HTTP_502_BAD_GATEWAY, f"Object storage error: {exc}") from exc

    photo = Photo(
        id=photo_id,
        owner_id=current_user.id,
        category=category,
        category_source="user" if category_provided else "fallback",
        user_message=user_message,
        ai_caption=None,
        final_caption=user_message,
        caption_source="user" if user_message else "none",
        ai_category_suggestion=None,
        ai_caption_enabled=ai_caption_enabled,
        ai_category_enabled=ai_category_enabled,
        include_in_showcase=include_in_showcase,
        time_source="uploaded_at",
        bucket=storage.bucket,
        object_key_original=original_key,
        object_key_thumbnail=thumbnail_key,
        object_key_preview=preview_key,
        mime_type=content_type,
        file_size=len(image_bytes),
        sha256=sha256,
        width=None,
        height=None,
        taken_at=uploaded_at,
        uploaded_at=uploaded_at,
        gps_lat=None,
        gps_lng=None,
        camera_make=None,
        camera_model=None,
        exif_json=None,
        status=PHOTO_STATUS_PROCESSING,
    )
    try:
        photo, _job = create_photo_with_processing_job(
            db,
            photo,
            max_attempts=settings.photo_job_max_attempts,
        )
    except PhotoJobCreateError as exc:
        storage.delete_object(original_key)
        raise UploadPhotoError(status.HTTP_409_CONFLICT, "Duplicate photo") from exc

    return PhotoRead.model_validate(photo).model_copy(
        update={"processing_message": "Photo uploaded and queued for processing"}
    )


@router.post("/upload", response_model=PhotoRead, status_code=status.HTTP_201_CREATED)
async def upload_photo(
    db: DbSession,
    settings: AppSettings,
    current_user: Annotated[User, Depends(get_current_user)],
    storage: Annotated[ObjectStorage, Depends(get_object_storage)],
    file: UploadFile = File(...),
    category: str | None = Form(default=None),
    user_message: str | None = Form(default=None),
    ai_caption_enabled: bool = Form(default=False),
    ai_category_enabled: bool = Form(default=False),
    include_in_showcase: bool = Form(default=True),
) -> PhotoRead:
    """Upload a photo original and enqueue asynchronous processing."""

    category_provided = bool(category)
    category = _validate_category(category, db)
    try:
        return await _upload_one_photo(
            db,
            settings,
            current_user,
            storage,
            file,
            category=category,
            category_provided=category_provided,
            user_message=user_message,
            ai_caption_enabled=ai_caption_enabled,
            ai_category_enabled=ai_category_enabled,
            include_in_showcase=include_in_showcase,
        )
    except UploadPhotoError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.post("/batch-upload", response_model=PhotoBatchUploadResponse, status_code=status.HTTP_201_CREATED)
async def batch_upload_photos(
    db: DbSession,
    settings: AppSettings,
    current_user: Annotated[User, Depends(get_current_user)],
    storage: Annotated[ObjectStorage, Depends(get_object_storage)],
    files: list[UploadFile] = File(...),
    category: str | None = Form(default=None),
    user_message: str | None = Form(default=None),
    ai_caption_enabled: bool = Form(default=False),
    ai_category_enabled: bool = Form(default=False),
    include_in_showcase: bool = Form(default=True),
) -> PhotoBatchUploadResponse:
    """Upload up to 10 photos and return independent per-file results."""

    category_provided = bool(category)
    category = _validate_category(category, db)
    if len(files) > BATCH_UPLOAD_MAX_FILES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Batch upload supports at most {BATCH_UPLOAD_MAX_FILES} files",
        )

    results: list[PhotoBatchUploadItem] = []
    for file in files:
        filename = file.filename or "upload"
        try:
            photo = await _upload_one_photo(
                db,
                settings,
                current_user,
                storage,
                file,
                category=category,
                category_provided=category_provided,
                user_message=user_message,
                ai_caption_enabled=ai_caption_enabled,
                ai_category_enabled=ai_category_enabled,
                include_in_showcase=include_in_showcase,
            )
            results.append(PhotoBatchUploadItem(filename=filename, success=True, photo=photo, error=None))
        except UploadPhotoError as exc:
            results.append(PhotoBatchUploadItem(filename=filename, success=False, photo=None, error=exc.detail))

    success_count = sum(1 for item in results if item.success)
    return PhotoBatchUploadResponse(
        success_count=success_count,
        failure_count=len(results) - success_count,
        results=results,
    )


@router.get("", response_model=list[PhotoRead])
def get_photos(
    db: DbSession,
    _current_user: Annotated[User, Depends(get_current_user)],
    category: str | None = Query(default=None),
) -> list[PhotoRead]:
    """List photos visible to logged-in users."""

    if category is not None:
        category = _validate_category(category, db)
    return [PhotoRead.model_validate(photo) for photo in list_photos(db, category)]


@router.get("/categories", response_model=list[PhotoCategoryRead])
def get_photo_categories(
    db: DbSession,
    _current_user: Annotated[User, Depends(get_current_user)],
) -> list[PhotoCategoryRead]:
    """Return the PRD default categories with legacy slug metadata."""

    return [PhotoCategoryRead.model_validate(category) for category in list_active_categories(db)]


@router.post("/{photo_id}/slide-designs", response_model=SlideDesignRead, status_code=status.HTTP_201_CREATED)
def post_slide_design(
    photo_id: str,
    payload: SlideDesignCreate,
    db: DbSession,
    current_user: Annotated[User, Depends(get_current_user)],
) -> SlideDesignRead:
    """Store one slide design version for a photo."""

    photo = _photo_or_404(db, photo_id)
    if not can_modify_photo(current_user, photo):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot modify this photo")
    try:
        return SlideDesignRead.model_validate(create_slide_design(db, photo_id, payload))
    except DuplicateSlideDesignVersionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Duplicate slide design version") from exc


@router.get("/{photo_id}/slide-design", response_model=SlideDesignRead)
def get_slide_design(
    photo_id: str,
    db: DbSession,
    _current_user: Annotated[User, Depends(get_current_user)],
) -> SlideDesignRead:
    """Return the latest active slide design for a photo."""

    _photo_or_404(db, photo_id)
    design = get_latest_active_slide_design(db, photo_id)
    if design is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Slide design not found")
    return SlideDesignRead.model_validate(design)


@router.get("/{photo_id}", response_model=PhotoRead)
def get_photo_detail(
    photo_id: str,
    db: DbSession,
    _current_user: Annotated[User, Depends(get_current_user)],
) -> PhotoRead:
    """Return one photo's metadata."""

    return PhotoRead.model_validate(_photo_or_404(db, photo_id))


@router.get("/{photo_id}/processing-status", response_model=PhotoProcessingStatusResponse)
def get_processing_status(
    photo_id: str,
    db: DbSession,
    _current_user: Annotated[User, Depends(get_current_user)],
) -> PhotoProcessingStatusResponse:
    """Return processing state for a photo."""

    photo = _photo_or_404(db, photo_id)
    job = get_latest_job_for_photo(db, photo_id)
    design = get_latest_active_slide_design(db, photo_id)
    return PhotoProcessingStatusResponse(
        photo_id=photo.id,
        photo_status=photo.status,
        job_type=job.job_type if job is not None else None,
        job_status=job.status if job is not None else None,
        attempts=job.attempts if job is not None else None,
        max_attempts=job.max_attempts if job is not None else None,
        error_message=job.error_message if job is not None else None,
        slide_design_status=design.status if design is not None else None,
        slide_design_source=design.source if design is not None else None,
        ai_provider=job.ai_provider if job is not None else None,
        ai_model=job.ai_model if job is not None else None,
        geocoding_status=photo.geocoding_status,
    )


@router.patch("/{photo_id}", response_model=PhotoRead)
def patch_photo(
    photo_id: str,
    payload: PhotoUpdate,
    db: DbSession,
    current_user: Annotated[User, Depends(get_current_user)],
) -> PhotoRead:
    """Update editable photo fields."""

    photo = _photo_or_404(db, photo_id)
    if not can_modify_photo(current_user, photo):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot modify this photo")
    previous_showcase_visibility = photo.include_in_showcase
    updated = update_photo(db, photo, payload)
    if (
        payload.include_in_showcase is not None
        and updated.include_in_showcase != previous_showcase_visibility
    ):
        action = "photo.unhide" if updated.include_in_showcase else "photo.hide"
        create_audit_log(
            db,
            admin_id=current_user.id,
            action=action,
            target_type="photo",
            target_id=updated.id,
            detail={
                "summary": "Photo shown in showcase" if updated.include_in_showcase else "Photo hidden from showcase",
                "before": {"include_in_showcase": previous_showcase_visibility},
                "after": {"include_in_showcase": updated.include_in_showcase},
            },
        )
    return PhotoRead.model_validate(updated)


@router.patch("/{photo_id}/message", response_model=PhotoRead)
def patch_photo_message(
    photo_id: str,
    payload: PhotoMessageUpdate,
    db: DbSession,
    current_user: Annotated[User, Depends(get_current_user)],
) -> PhotoRead:
    """Update the user_message on a photo (owner only, respects admin override)."""
    photo = _photo_or_404(db, photo_id)
    try:
        updated = update_user_message(db, photo, current_user, payload.user_message)
    except PhotoPermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only edit the message on your own photos",
        )
    return PhotoRead.model_validate(updated)


@router.delete("/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_photo_endpoint(
    photo_id: str,
    db: DbSession,
    current_user: Annotated[User, Depends(get_current_user)],
    storage: Annotated[ObjectStorage, Depends(get_object_storage)],
) -> None:
    """Delete a photo record and its stored objects."""

    photo = _photo_or_404(db, photo_id)
    if not can_modify_photo(current_user, photo):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot delete this photo")
    storage.delete_object(photo.object_key_original)
    storage.delete_object(photo.object_key_thumbnail)
    if photo.object_key_preview is not None:
        storage.delete_object(photo.object_key_preview)
    delete_photo(db, photo)


@router.get("/{photo_id}/thumbnail-url", response_model=PresignedUrlResponse)
def get_thumbnail_url(
    photo_id: str,
    db: DbSession,
    _current_user: Annotated[User, Depends(get_current_user)],
    storage: Annotated[ObjectStorage, Depends(get_object_storage)],
) -> PresignedUrlResponse:
    """Return a short-lived thumbnail URL."""

    photo = _photo_or_404(db, photo_id)
    return PresignedUrlResponse(url=storage.presigned_get_url(photo.object_key_thumbnail))


@router.get("/{photo_id}/preview-url", response_model=PresignedUrlResponse)
def get_preview_url(
    photo_id: str,
    db: DbSession,
    _current_user: Annotated[User, Depends(get_current_user)],
    storage: Annotated[ObjectStorage, Depends(get_object_storage)],
) -> PresignedUrlResponse:
    """Return a short-lived preview URL."""

    photo = _photo_or_404(db, photo_id)
    if photo.object_key_preview is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preview not available")
    return PresignedUrlResponse(url=storage.presigned_get_url(photo.object_key_preview))


@router.get("/{photo_id}/original-url", response_model=PresignedUrlResponse)
def get_original_url(
    photo_id: str,
    db: DbSession,
    _current_user: Annotated[User, Depends(get_current_user)],
    storage: Annotated[ObjectStorage, Depends(get_object_storage)],
) -> PresignedUrlResponse:
    """Return a short-lived original image URL."""

    photo = _photo_or_404(db, photo_id)
    return PresignedUrlResponse(url=storage.presigned_get_url(photo.object_key_original))
