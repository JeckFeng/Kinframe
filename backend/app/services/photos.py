"""Photo persistence and permission helpers."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Photo, User
from app.schemas.photo import PhotoUpdate
from app.services.categories import PHOTO_ACCEPTED_CATEGORY_SLUGS, photo_category_filter_values

PHOTO_CATEGORIES = PHOTO_ACCEPTED_CATEGORY_SLUGS
PHOTO_STATUS_UPLOADED = "uploaded"
PHOTO_STATUS_PROCESSING = "processing"
PHOTO_STATUS_EXIF_PARSED = "exif_parsed"
PHOTO_STATUS_PREVIEW_GENERATED = "preview_generated"
PHOTO_STATUS_VISION_ANALYZED = "vision_analyzed"
PHOTO_STATUS_DESIGN_GENERATED = "design_generated"
PHOTO_STATUS_READY = "ready"
PHOTO_STATUS_FAILED = "failed"
PHOTO_STATUS_CONFIRMED = PHOTO_STATUS_READY
PHOTO_STATUSES = {
    PHOTO_STATUS_UPLOADED,
    PHOTO_STATUS_PROCESSING,
    PHOTO_STATUS_EXIF_PARSED,
    PHOTO_STATUS_PREVIEW_GENERATED,
    PHOTO_STATUS_VISION_ANALYZED,
    PHOTO_STATUS_DESIGN_GENERATED,
    PHOTO_STATUS_READY,
    PHOTO_STATUS_FAILED,
}


class DuplicatePhotoError(ValueError):
    """Raised when a photo with the same SHA-256 already exists."""


def utc_now() -> datetime:
    """Return the current UTC timestamp."""

    return datetime.now(timezone.utc)


def get_photo(db: Session, photo_id: str) -> Photo | None:
    """Return a photo by ID."""

    return db.get(Photo, photo_id)


def get_photo_by_sha256(db: Session, sha256: str) -> Photo | None:
    """Return a photo by SHA-256 hash."""

    return db.scalar(select(Photo).where(Photo.sha256 == sha256))


def list_photos(db: Session, category: str | None = None) -> list[Photo]:
    """Return visible photos, optionally filtered by category."""

    statement = select(Photo).order_by(Photo.uploaded_at.desc(), Photo.created_at.desc())
    if category is not None:
        statement = statement.where(Photo.category.in_(photo_category_filter_values(category)))
    return list(db.scalars(statement))


def create_photo(db: Session, photo: Photo) -> Photo:
    """Persist a new photo."""

    db.add(photo)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DuplicatePhotoError(photo.sha256) from exc
    db.refresh(photo)
    return photo


def can_modify_photo(user: User, photo: Photo) -> bool:
    """Return whether a user can modify or delete a photo."""

    return user.role == "admin" or photo.owner_id == user.id


def update_photo(db: Session, photo: Photo, payload: PhotoUpdate) -> Photo:
    """Apply user-editable fields to a photo."""

    data = payload.model_dump(exclude_unset=True)
    if "category" in data and data["category"] is not None:
        photo.category = data["category"]
    if "user_message" in data:
        photo.user_message = data["user_message"]
        photo.final_caption = data["user_message"]
    if "ai_caption_enabled" in data and data["ai_caption_enabled"] is not None:
        photo.ai_caption_enabled = data["ai_caption_enabled"]
    if "ai_category_enabled" in data and data["ai_category_enabled"] is not None:
        photo.ai_category_enabled = data["ai_category_enabled"]
    if "include_in_showcase" in data and data["include_in_showcase"] is not None:
        photo.include_in_showcase = data["include_in_showcase"]
    photo.updated_at = utc_now()
    db.add(photo)
    db.commit()
    db.refresh(photo)
    return photo


def delete_photo(db: Session, photo: Photo) -> None:
    """Delete a photo database record."""

    db.delete(photo)
    db.commit()
