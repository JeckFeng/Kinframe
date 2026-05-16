"""Admin photo management routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import AppSettings, DbSession, get_current_admin
from app.models import User
from app.schemas.photo import AdminPhotoListResponse, AdminPhotoUpdate, ManualSlideDesignCreate, PhotoAdminRead, RegenerateScope
from app.services.admin_photos import build_admin_photo_detail, list_admin_photos
from app.services.audit_logs import create_audit_log
from app.services.photos import (
    get_photo,
    reset_photo_caption,
    update_photo_admin,
)
from app.services.slide_designs import (
    DuplicateSlideDesignVersionError,
    SlideDesignNotFoundError,
    activate_slide_design,
    create_manual_slide_design,
)

router = APIRouter(prefix="/api/admin/photos", tags=["admin-photos"])


def _photo_or_404(db: DbSession, photo_id: str):
    from app.models import Photo
    photo = get_photo(db, photo_id)
    if photo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found")
    return photo


@router.get("", response_model=AdminPhotoListResponse)
def get_admin_photos(
    db: DbSession,
    _admin: Annotated[User, Depends(get_current_admin)],
    category: str | None = Query(default=None),
    geocoding_status: str | None = Query(default=None),
    showcase_visibility: str | None = Query(default=None, pattern="^(visible|hidden)$"),
    ai_status: str | None = Query(default=None),
    design_source: str | None = Query(default=None),
    failed_only: bool = Query(default=False),
    needs_review: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> AdminPhotoListResponse:
    items, total = list_admin_photos(
        db,
        category=category,
        geocoding_status=geocoding_status,
        showcase_visibility=showcase_visibility,
        ai_status=ai_status,
        design_source=design_source,
        failed_only=failed_only,
        needs_review=needs_review,
        limit=limit,
        offset=offset,
    )
    return AdminPhotoListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/{photo_id}", response_model=PhotoAdminRead)
def get_admin_photo(
    photo_id: str,
    db: DbSession,
    _admin: Annotated[User, Depends(get_current_admin)],
) -> PhotoAdminRead:
    """Return full photo metadata including AI diagnostics, EXIF, errors."""
    return build_admin_photo_detail(db, _photo_or_404(db, photo_id))


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
    return build_admin_photo_detail(db, photo)


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


@router.post("/{photo_id}/delete", status_code=status.HTTP_201_CREATED)
def enqueue_photo_delete(
    photo_id: str,
    db: DbSession,
    settings: AppSettings,
    admin: Annotated[User, Depends(get_current_admin)],
) -> dict:
    """Enqueue a background photo_purge job for permanent deletion."""
    photo = _photo_or_404(db, photo_id)

    from app.services.photo_jobs import PHOTO_JOB_TYPE_PHOTO_PURGE, create_photo_purge_job

    job = create_photo_purge_job(
        db,
        photo_id=photo.id,
        max_attempts=1,
    )
    create_audit_log(
        db,
        admin_id=admin.id,
        action="photo.delete_requested",
        target_type="photo",
        target_id=photo_id,
        detail={
            "job_id": job.id,
            "job_type": PHOTO_JOB_TYPE_PHOTO_PURGE,
            "summary": f"Admin {admin.username} requested permanent photo deletion",
        },
    )
    return {"photo_id": photo.id, "job_id": job.id, "job_type": PHOTO_JOB_TYPE_PHOTO_PURGE}


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
    return (
        bool(settings.ai_enabled)
        and bool(settings.deepseek_api_key and settings.deepseek_api_key.strip())
        and bool(settings.deepseek_model and settings.deepseek_model.strip())
    )


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
        PHOTO_JOB_TYPE_CAPTION_REGENERATE,
        PHOTO_JOB_TYPE_CSS_REGENERATE,
        PHOTO_JOB_TYPE_FALLBACK_REGENERATE,
        PHOTO_JOB_TYPE_SLIDE_DESIGN_GENERATE,
        PHOTO_JOB_TYPE_TEMPLATE_REGENERATE,
        create_caption_regenerate_job,
        create_css_regenerate_job,
        create_fallback_regenerate_job,
        create_slide_design_generate_job,
        create_template_regenerate_job,
    )

    if payload.scope == "fallback":
        job = create_fallback_regenerate_job(
            db,
            photo.id,
            max_attempts=1,
        )
        create_audit_log(
            db,
            admin_id=admin.id,
            action="photo.regenerate",
            target_type="photo",
            target_id=photo_id,
            detail={
                "scope": "fallback",
                "job_id": job.id,
                "job_type": PHOTO_JOB_TYPE_FALLBACK_REGENERATE,
                "summary": f"Admin {admin.username} regenerated fallback design for photo",
            },
        )
        return {"photo_id": photo.id, "scope": payload.scope, "job_id": job.id, "job_type": PHOTO_JOB_TYPE_FALLBACK_REGENERATE}

    if payload.scope == "caption":
        job = create_caption_regenerate_job(
            db,
            photo_id=photo.id,
            max_attempts=settings.ai_max_retries + 1,
            provider_name="deepseek",
        )
        job_type = PHOTO_JOB_TYPE_CAPTION_REGENERATE
    elif payload.scope == "template":
        job = create_template_regenerate_job(
            db,
            photo_id=photo.id,
            max_attempts=settings.ai_max_retries + 1,
            provider_name="deepseek",
        )
        job_type = PHOTO_JOB_TYPE_TEMPLATE_REGENERATE
    elif payload.scope == "css_tokens":
        job = create_css_regenerate_job(
            db,
            photo_id=photo.id,
            max_attempts=settings.ai_max_retries + 1,
            provider_name="deepseek",
        )
        job_type = PHOTO_JOB_TYPE_CSS_REGENERATE
    else:
        job = create_slide_design_generate_job(
            db,
            photo_id=photo.id,
            max_attempts=settings.ai_max_retries + 1,
            provider_name="deepseek",
        )
        job_type = PHOTO_JOB_TYPE_SLIDE_DESIGN_GENERATE

    create_audit_log(
        db,
        admin_id=admin.id,
        action="photo.regenerate",
        target_type="photo",
        target_id=photo_id,
        detail={
            "scope": payload.scope,
            "job_id": job.id,
            "job_type": job_type,
            "summary": f"Admin {admin.username} requested {payload.scope} regeneration for photo",
        },
    )
    return {"photo_id": photo.id, "job_id": job.id, "job_type": job_type, "scope": payload.scope}


@router.post("/{photo_id}/design-versions/{design_id}/activate", response_model=PhotoAdminRead)
def activate_design_version(
    photo_id: str,
    design_id: str,
    db: DbSession,
    admin: Annotated[User, Depends(get_current_admin)],
) -> PhotoAdminRead:
    photo = _photo_or_404(db, photo_id)
    try:
        design = activate_slide_design(db, photo_id, design_id)
    except SlideDesignNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Slide design version not found") from exc

    create_audit_log(
        db,
        admin_id=admin.id,
        action="design.activate",
        target_type="slide_design",
        target_id=design.id,
        detail={
            "photo_id": photo_id,
            "version": design.version,
            "source": design.source,
            "summary": f"Admin {admin.username} set slide design v{design.version} active",
        },
    )
    return build_admin_photo_detail(db, photo)


@router.post("/{photo_id}/design-versions/manual", response_model=PhotoAdminRead, status_code=status.HTTP_201_CREATED)
def create_manual_design_version(
    photo_id: str,
    payload: ManualSlideDesignCreate,
    db: DbSession,
    admin: Annotated[User, Depends(get_current_admin)],
) -> PhotoAdminRead:
    photo = _photo_or_404(db, photo_id)
    try:
        design = create_manual_slide_design(
            db,
            photo_id,
            design_json=payload.design_json,
            activate=payload.activate,
        )
    except DuplicateSlideDesignVersionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Concurrent slide design version conflict") from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    create_audit_log(
        db,
        admin_id=admin.id,
        action="design.manual_create",
        target_type="slide_design",
        target_id=design.id,
        detail={
            "photo_id": photo_id,
            "version": design.version,
            "status": design.status,
            "activate": payload.activate,
            "summary": f"Admin {admin.username} created manual slide design v{design.version}",
        },
    )
    return build_admin_photo_detail(db, photo)
