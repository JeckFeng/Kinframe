"""Slide design persistence helpers."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import SlideDesign
from app.schemas.photo import SlideDesignCreate

SLIDE_DESIGN_STATUS_ACTIVE = "active"


class DuplicateSlideDesignVersionError(ValueError):
    """Raised when a photo already has a design with the requested version."""


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
