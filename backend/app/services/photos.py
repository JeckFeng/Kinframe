"""Photo persistence and permission helpers."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Photo, User
from app.schemas.photo import AdminPhotoUpdate, PhotoUpdate
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


def compute_final_caption(photo: Photo) -> tuple[str | None, str]:
    """Compute final_caption and caption_source from photo fields.

    Priority: manual admin override > user_message > ai_caption > None.
    Returns (final_caption, caption_source).
    """
    # Admin manual override takes absolute priority
    if photo.caption_source == "admin" and photo.final_caption is not None:
        return photo.final_caption, "admin"

    if photo.user_message:
        return photo.user_message, "user"
    if photo.ai_caption and photo.ai_caption_enabled:
        return photo.ai_caption, "ai"
    return None, "none"


def update_photo(db: Session, photo: Photo, payload: PhotoUpdate) -> Photo:
    """Apply user-editable fields to a photo."""

    data = payload.model_dump(exclude_unset=True)
    if "category" in data and data["category"] is not None:
        photo.category = data["category"]
    if "user_message" in data:
        photo.user_message = data["user_message"]
        # Only recompute final_caption if admin hasn't manually overridden
        if photo.caption_source != "admin":
            final, source = compute_final_caption(photo)
            photo.final_caption = final
            photo.caption_source = source
    if "ai_caption_enabled" in data and data["ai_caption_enabled"] is not None:
        photo.ai_caption_enabled = data["ai_caption_enabled"]
        if photo.caption_source != "admin":
            final, source = compute_final_caption(photo)
            photo.final_caption = final
            photo.caption_source = source
    if "ai_category_enabled" in data and data["ai_category_enabled"] is not None:
        photo.ai_category_enabled = data["ai_category_enabled"]
    if "include_in_showcase" in data and data["include_in_showcase"] is not None:
        photo.include_in_showcase = data["include_in_showcase"]
    photo.updated_at = utc_now()
    db.add(photo)
    db.commit()
    db.refresh(photo)
    return photo


def update_photo_admin(
    db: Session,
    photo: Photo,
    payload: AdminPhotoUpdate,
    *,
    admin_user: User,
) -> dict:
    """Apply admin-editable fields and return changed_fields for audit logging."""

    data = payload.model_dump(exclude_unset=True)
    changed_fields: list[str] = []
    before: dict = {}
    after: dict = {}

    # Category change — auto-set category_source
    if "category" in data and data["category"] is not None and data["category"] != photo.category:
        changed_fields.append("category")
        changed_fields.append("category_source")
        before["category"] = photo.category
        before["category_source"] = photo.category_source
        photo.category = data["category"]
        photo.category_source = f"admin:{admin_user.username}"
        after["category"] = photo.category
        after["category_source"] = photo.category_source

    # final_caption manual override
    if "final_caption" in data:
        old_caption = photo.final_caption
        old_source = photo.caption_source
        new_caption = data["final_caption"]
        if new_caption != old_caption or photo.caption_source != "admin":
            changed_fields.append("final_caption")
            changed_fields.append("caption_source")
            before["final_caption"] = old_caption
            before["caption_source"] = old_source
            photo.final_caption = new_caption
            photo.caption_source = "admin" if new_caption is not None else "none"
            after["final_caption"] = photo.final_caption
            after["caption_source"] = photo.caption_source

    # Location fields
    for loc_field in (
        "location_name", "location_country", "location_region",
        "location_city", "location_district", "location_road",
    ):
        if loc_field in data and data[loc_field] is not None:
            old_val = getattr(photo, loc_field)
            new_val = data[loc_field]
            if new_val != old_val:
                changed_fields.append(loc_field)
                before[loc_field] = old_val
                after[loc_field] = new_val
                setattr(photo, loc_field, new_val)

    if changed_fields:
        photo.updated_at = utc_now()
        db.add(photo)
        db.commit()
        db.refresh(photo)
        return {
            "changed_fields": changed_fields,
            "before": before,
            "after": after,
        }

    return {"changed_fields": [], "before": {}, "after": {}}


def reset_photo_caption(db: Session, photo: Photo) -> dict:
    """Clear admin caption override and recompute from user_message / ai_caption."""

    old_caption = photo.final_caption
    old_source = photo.caption_source

    photo.caption_source = "none"
    final, source = compute_final_caption(photo)
    photo.final_caption = final
    photo.caption_source = source
    photo.updated_at = utc_now()
    db.add(photo)
    db.commit()
    db.refresh(photo)

    return {
        "changed_fields": ["final_caption", "caption_source"],
        "before": {"final_caption": old_caption, "caption_source": old_source},
        "after": {"final_caption": photo.final_caption, "caption_source": photo.caption_source},
    }


def delete_photo(db: Session, photo: Photo) -> None:
    """Delete a photo database record."""

    db.delete(photo)
    db.commit()
