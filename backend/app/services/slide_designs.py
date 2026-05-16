"""Slide design persistence helpers."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import SlideDesign
from app.schemas.photo import SlideDesignCreate

SLIDE_DESIGN_STATUS_ACTIVE = "active"


class DuplicateSlideDesignVersionError(ValueError):
    """Raised when a photo already has a design with the requested version."""


class SlideDesignNotFoundError(ValueError):
    """Raised when a requested slide design does not exist for the photo."""


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def create_slide_design(db: Session, photo_id: str, payload: SlideDesignCreate) -> SlideDesign:
    """Persist one slide design version for a photo."""

    design = SlideDesign(
        photo_id=photo_id,
        version=payload.version,
        design_json=payload.design_json,
        source=payload.source,
        status=payload.status,
        validation_errors=payload.validation_errors,
    )
    db.add(design)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DuplicateSlideDesignVersionError(f"{photo_id}:{payload.version}") from exc
    db.refresh(design)
    return design


def get_latest_active_slide_design(db: Session, photo_id: str) -> SlideDesign | None:
    """Return the highest active design version for a photo."""

    return db.scalar(
        select(SlideDesign)
        .where(
            SlideDesign.photo_id == photo_id,
            SlideDesign.status == SLIDE_DESIGN_STATUS_ACTIVE,
        )
        .order_by(SlideDesign.version.desc(), SlideDesign.created_at.desc())
    )


def get_latest_slide_design_version(db: Session, photo_id: str) -> int:
    """Return latest stored design version for a photo, or 0 when absent."""

    version = db.scalar(
        select(SlideDesign.version)
        .where(SlideDesign.photo_id == photo_id)
        .order_by(SlideDesign.version.desc())
    )
    return int(version or 0)


def get_slide_design(db: Session, photo_id: str, design_id: str) -> SlideDesign | None:
    return db.scalar(
        select(SlideDesign).where(
            SlideDesign.id == design_id,
            SlideDesign.photo_id == photo_id,
        )
    )


def activate_slide_design(db: Session, photo_id: str, design_id: str) -> SlideDesign:
    design = get_slide_design(db, photo_id, design_id)
    if design is None:
        raise SlideDesignNotFoundError(f"{photo_id}:{design_id}")

    now = utc_now()
    active_design = get_latest_active_slide_design(db, photo_id)
    if active_design is not None and active_design.id != design.id:
        active_design.status = "draft"
        active_design.updated_at = now
        db.add(active_design)

    design.status = "active"
    design.updated_at = now
    db.add(design)
    db.commit()
    db.refresh(design)
    return design


def create_manual_slide_design(
    db: Session,
    photo_id: str,
    *,
    design_json: dict,
    activate: bool = False,
) -> SlideDesign:
    from app.schemas.slide_design_validator import validate_slide_design_data

    validated = validate_slide_design_data(design_json, photo_id=photo_id)
    status = "active" if activate else "draft"

    for _ in range(3):
        version = get_latest_slide_design_version(db, photo_id) + 1
        design = SlideDesign(
            photo_id=photo_id,
            version=version,
            design_json=validated,
            source="manual",
            status=status,
            validation_errors=None,
        )
        now = utc_now()
        if activate:
            active_design = get_latest_active_slide_design(db, photo_id)
            if active_design is not None:
                active_design.status = "draft"
                active_design.updated_at = now
                db.add(active_design)
        db.add(design)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            continue
        db.refresh(design)
        return design

    raise DuplicateSlideDesignVersionError(f"{photo_id}:manual")
