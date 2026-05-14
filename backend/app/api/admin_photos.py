"""Admin photo management routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import AppSettings, DbSession, get_current_admin
from app.models import User
from app.schemas.photo import AdminPhotoUpdate, PhotoAdminRead, RegenerateScope
from app.services.audit_logs import create_audit_log
from app.services.photos import (
    get_photo,
    reset_photo_caption,
    update_photo_admin,
)

router = APIRouter(prefix="/api/admin/photos", tags=["admin-photos"])


def _photo_or_404(db: DbSession, photo_id: str):
    from app.models import Photo
    photo = get_photo(db, photo_id)
    if photo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found")
    return photo


@router.get("/{photo_id}", response_model=PhotoAdminRead)
def get_admin_photo(
    photo_id: str,
    db: DbSession,
    _admin: Annotated[User, Depends(get_current_admin)],
) -> PhotoAdminRead:
    """Return full photo metadata including AI diagnostics, EXIF, errors."""
    return PhotoAdminRead.model_validate(_photo_or_404(db, photo_id))


@router.patch("/{photo_id}", response_model=PhotoAdminRead)
def patch_admin_photo(
    photo_id: str,
    payload: AdminPhotoUpdate,
    db: DbSession,
    admin: Annotated[User, Depends(get_current_admin)],
) -> PhotoAdminRead:
    """Update photo fields with admin privileges. Category change auto-sets source."""
    photo = _photo_or_404(db, photo_id)
    audit_info = update_photo_admin(db, photo, payload, admin_user=admin)
    if audit_info["changed_fields"]:
        create_audit_log(
            db,
            admin_id=admin.id,
            action="photo.update",
            target_type="photo",
            target_id=photo_id,
            detail={
                "changed_fields": audit_info["changed_fields"],
                "before": audit_info["before"],
                "after": audit_info["after"],
                "summary": f"Admin {admin.username} updated photo fields",
            },
        )
    return PhotoAdminRead.model_validate(photo)


@router.post("/{photo_id}/reset-caption")
def reset_caption(
    photo_id: str,
    db: DbSession,
    admin: Annotated[User, Depends(get_current_admin)],
) -> dict:
    """Clear admin caption override and recompute from user_message / ai_caption."""
    photo = _photo_or_404(db, photo_id)
    audit_info = reset_photo_caption(db, photo)
    create_audit_log(
        db,
        admin_id=admin.id,
        action="photo.caption_reset",
        target_type="photo",
        target_id=photo_id,
        detail={
            "changed_fields": audit_info["changed_fields"],
            "before": audit_info["before"],
            "after": audit_info["after"],
            "summary": f"Admin {admin.username} reset photo caption",
        },
    )
    return {
        "photo_id": photo.id,
        "final_caption": photo.final_caption,
        "caption_source": photo.caption_source,
    }


@router.post("/{photo_id}/regenerate-design", status_code=status.HTTP_201_CREATED)
def regenerate_design(
    photo_id: str,
    db: DbSession,
    settings: AppSettings,
    admin: Annotated[User, Depends(get_current_admin)],
) -> dict:
    """Enqueue a new slide_design_generate job for this photo."""
    photo = _photo_or_404(db, photo_id)
    from app.services.photo_jobs import create_slide_design_generate_job
    job = create_slide_design_generate_job(
        db,
        photo_id=photo.id,
        max_attempts=settings.ai_max_retries + 1,
        provider_name="deepseek",
    )
    create_audit_log(
        db,
        admin_id=admin.id,
        action="photo.regenerate_design",
        target_type="photo",
        target_id=photo_id,
        detail={
            "job_id": job.id,
            "job_type": "slide_design_generate",
            "summary": f"Admin {admin.username} requested slide design regeneration",
        },
    )
    return {"photo_id": photo.id, "job_id": job.id, "job_type": job.job_type}


AI_REQUIRED_SCOPES = {"caption", "template", "css_tokens", "full"}


def _ai_enabled(settings: AppSettings) -> bool:
    return bool(settings.deepseek_api_key and settings.deepseek_api_key.strip())


@router.post("/{photo_id}/regenerate", status_code=status.HTTP_201_CREATED)
def regenerate_photo(
    photo_id: str,
    payload: RegenerateScope,
    db: DbSession,
    settings: AppSettings,
    admin: Annotated[User, Depends(get_current_admin)],
) -> dict:
    """Regenerate specific aspects of a photo with granular scope."""
    photo = _photo_or_404(db, photo_id)

    if payload.scope in AI_REQUIRED_SCOPES and not _ai_enabled(settings):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Scope '{payload.scope}' requires AI but AI is disabled (deepseek_api_key not configured)",
        )

    from app.services.photo_jobs import (
        PHOTO_JOB_STATUS_PENDING,
        create_slide_design_generate_job,
    )
    from app.services.fallback_slide_design import build_fallback_slide_design
    from app.services.slide_designs import (
        SLIDE_DESIGN_STATUS_ACTIVE,
        get_latest_active_slide_design,
        get_latest_slide_design_version,
        create_slide_design,
    )
    from app.schemas.photo import SlideDesignCreate
    from app.services.exif import ExtractedMetadata
    from datetime import datetime, timezone

    if payload.scope == "fallback":
        # Generate deterministic fallback directly
        from app.services.exif import ExtractedMetadata
        metadata = ExtractedMetadata(
            width=photo.width, height=photo.height,
            taken_at=photo.taken_at,
            gps_lat=photo.gps_lat, gps_lng=photo.gps_lng,
            camera_make=photo.camera_make, camera_model=photo.camera_model,
            exif_json=photo.exif_json,
        )
        design_json = build_fallback_slide_design(photo, metadata)

        active_design = get_latest_active_slide_design(db, photo.id)
        now = datetime.now(timezone.utc)
        if active_design is not None and active_design.status == SLIDE_DESIGN_STATUS_ACTIVE:
            active_design.status = "draft"
            active_design.updated_at = now
            db.add(active_design)

        version = get_latest_slide_design_version(db, photo.id) + 1
        create_slide_design(
            db, photo.id,
            SlideDesignCreate(
                version=version, design_json=design_json,
                source="fallback", status="active", validation_errors=None,
            ),
        )
        photo.updated_at = now
        db.add(photo)
        db.commit()

        create_audit_log(
            db,
            admin_id=admin.id,
            action="photo.regenerate",
            target_type="photo",
            target_id=photo_id,
            detail={
                "scope": "fallback",
                "summary": f"Admin {admin.username} regenerated fallback design for photo",
            },
        )
        return {"photo_id": photo.id, "scope": payload.scope}

    # AI-required scopes: enqueue slide_design_generate job
    job = create_slide_design_generate_job(
        db,
        photo_id=photo.id,
        max_attempts=settings.ai_max_retries + 1,
        provider_name="deepseek",
    )
    create_audit_log(
        db,
        admin_id=admin.id,
        action="photo.regenerate",
        target_type="photo",
        target_id=photo_id,
        detail={
            "scope": payload.scope,
            "job_id": job.id,
            "job_type": job.job_type,
            "summary": f"Admin {admin.username} requested {payload.scope} regeneration for photo",
        },
    )
    return {"photo_id": photo.id, "job_id": job.id, "job_type": job.job_type, "scope": payload.scope}
