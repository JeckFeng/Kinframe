"""Admin-facing photo query helpers for operational views."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog, Photo, PhotoProcessingJob, SlideDesign
from app.schemas.photo import (
    AdminAuditLogRead,
    AdminPhotoJobRead,
    AdminPhotoListItem,
    PhotoAdminRead,
    QualityReportRead,
    SlideDesignSummaryRead,
)
from app.services.ai.quality_scorer import score_design_quality
from app.schemas.slide_design_assets import get_template_definition


def _max_extra_layers_for(design_json: dict) -> int:
    template_id = design_json.get("templateId")
    template_def = get_template_definition(template_id) if isinstance(template_id, str) else None
    if isinstance(template_def, dict) and isinstance(template_def.get("maxExtraLayers"), int):
        return int(template_def["maxExtraLayers"])
    return 4


def build_quality_report(design_json: dict | None) -> QualityReportRead | None:
    if not isinstance(design_json, dict):
        return None
    try:
        report = score_design_quality(
            design_json,
            max_extra_layers=_max_extra_layers_for(design_json),
        )
    except Exception:
        return None
    return QualityReportRead(
        total_score=report.total_score,
        passed=report.passed,
        failures=list(report.failures or []),
    )


def _derive_ai_status(photo: Photo, jobs: list[object]) -> str:
    if photo.ai_analysis_json or photo.ai_caption or photo.ai_category_suggestion:
        return "analyzed"
    for job in jobs:
        job_type = getattr(job, "job_type", None)
        job_status = getattr(job, "status", None)
        if job_type in {
            "vision_analyze",
            "slide_design_generate",
            "caption_regenerate",
            "template_regenerate",
            "css_regenerate",
        } and job_status == "failed":
            return "failed"
    return "missing"


def _derive_needs_review(photo: Photo, active_design: object | None, has_failed_jobs: bool) -> bool:
    if has_failed_jobs:
        return True
    if photo.status == "failed" or photo.geocoding_status == "failed":
        return True
    return active_design is None or getattr(active_design, "source", None) == "fallback"


def list_photo_design_versions(db: Session, photo_id: str, *, limit: int = 10) -> list[SlideDesignSummaryRead]:
    rows = list(
        db.scalars(
            select(SlideDesign)
            .where(SlideDesign.photo_id == photo_id)
            .order_by(SlideDesign.version.desc(), SlideDesign.created_at.desc())
            .limit(limit)
        )
    )
    items: list[SlideDesignSummaryRead] = []
    for design in rows:
        design_json = design.design_json if isinstance(design.design_json, dict) else {}
        layers = design_json.get("layers", [])
        items.append(
            SlideDesignSummaryRead(
                id=design.id,
                version=design.version,
                source=design.source,
                status=design.status,
                design_json=design_json,
                template_id=design_json.get("templateId") if isinstance(design_json.get("templateId"), str) else None,
                layer_count=len(layers) if isinstance(layers, list) else 0,
                quality_report=build_quality_report(design_json),
                validation_errors=design.validation_errors,
                created_at=design.created_at,
                updated_at=design.updated_at,
            )
        )
    return items


def list_photo_recent_jobs(db: Session, photo_id: str, *, limit: int = 6) -> list[AdminPhotoJobRead]:
    rows = list(
        db.scalars(
            select(PhotoProcessingJob)
            .where(PhotoProcessingJob.photo_id == photo_id)
            .order_by(PhotoProcessingJob.created_at.desc(), PhotoProcessingJob.updated_at.desc())
            .limit(limit)
        )
    )
    return [
        AdminPhotoJobRead(
            id=job.id,
            job_type=job.job_type,
            status=job.status,
            attempts=job.attempts,
            max_attempts=job.max_attempts,
            error_message=job.error_message,
            ai_provider=job.ai_provider,
            ai_model=job.ai_model,
            ai_prompt_version=job.ai_prompt_version,
            ai_raw_summary=job.ai_raw_summary,
            started_at=job.started_at,
            finished_at=job.finished_at,
            created_at=job.created_at,
        )
        for job in rows
    ]


def list_photo_recent_audit_logs(db: Session, photo_id: str, *, limit: int = 6) -> list[AdminAuditLogRead]:
    rows = list(
        db.scalars(
            select(AuditLog)
            .where(
                AuditLog.target_type == "photo",
                AuditLog.target_id == photo_id,
            )
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        )
    )
    items: list[AdminAuditLogRead] = []
    for row in rows:
        detail = row.detail if isinstance(row.detail, dict) else None
        summary = detail.get("summary") if isinstance(detail, dict) else None
        items.append(
            AdminAuditLogRead(
                id=row.id,
                action=row.action,
                target_type=row.target_type,
                target_id=row.target_id,
                summary=summary if isinstance(summary, str) else None,
                detail=detail,
                created_at=row.created_at,
            )
        )
    return items


def build_admin_photo_detail(db: Session, photo: Photo) -> PhotoAdminRead:
    designs = list_photo_design_versions(db, photo.id, limit=12)
    jobs = list_photo_recent_jobs(db, photo.id, limit=8)
    audit_logs = list_photo_recent_audit_logs(db, photo.id, limit=8)
    active_design = next((d for d in designs if d.status == "active"), None)
    has_failed_jobs = any(job.status == "failed" for job in jobs)
    latest_job = jobs[0] if jobs else None

    return PhotoAdminRead.model_validate(photo).model_copy(
        update={
            "active_design_source": active_design.source if active_design else None,
            "active_design_version": active_design.version if active_design else None,
            "latest_job_type": latest_job.job_type if latest_job else None,
            "latest_job_status": latest_job.status if latest_job else None,
            "latest_job_error": latest_job.error_message if latest_job else None,
            "ai_status": _derive_ai_status(photo, jobs),
            "has_failed_jobs": has_failed_jobs,
            "needs_review": _derive_needs_review(photo, active_design, has_failed_jobs),
            "design_versions": designs,
            "recent_jobs": jobs,
            "recent_audit_logs": audit_logs,
        }
    )


def list_admin_photos(
    db: Session,
    *,
    category: str | None = None,
    geocoding_status: str | None = None,
    ai_status: str | None = None,
    design_source: str | None = None,
    failed_only: bool = False,
    needs_review: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[AdminPhotoListItem], int]:
    photos = list(
        db.scalars(
            select(Photo).order_by(Photo.uploaded_at.desc(), Photo.created_at.desc())
        )
    )
    photo_ids = [photo.id for photo in photos]
    active_design_rows = list(
        db.scalars(
            select(SlideDesign)
            .where(
                SlideDesign.photo_id.in_(photo_ids) if photo_ids else False,
                SlideDesign.status == "active",
            )
            .order_by(SlideDesign.photo_id, SlideDesign.version.desc(), SlideDesign.created_at.desc())
        )
    ) if photo_ids else []
    jobs = list(
        db.scalars(
            select(PhotoProcessingJob)
            .where(PhotoProcessingJob.photo_id.in_(photo_ids) if photo_ids else False)
            .order_by(PhotoProcessingJob.photo_id, PhotoProcessingJob.created_at.desc(), PhotoProcessingJob.updated_at.desc())
        )
    ) if photo_ids else []

    active_by_photo: dict[str, SlideDesign] = {}
    for design in active_design_rows:
        active_by_photo.setdefault(design.photo_id, design)

    jobs_by_photo: dict[str, list[PhotoProcessingJob]] = {}
    for job in jobs:
        jobs_by_photo.setdefault(job.photo_id, []).append(job)

    items: list[AdminPhotoListItem] = []
    for photo in photos:
        if category and photo.category != category:
            continue
        if geocoding_status and photo.geocoding_status != geocoding_status:
            continue

        photo_jobs = jobs_by_photo.get(photo.id, [])
        latest_job = photo_jobs[0] if photo_jobs else None
        has_failed_jobs = any(job.status == "failed" for job in photo_jobs)
        derived_ai_status = _derive_ai_status(photo, photo_jobs)
        active_design = active_by_photo.get(photo.id)
        derived_needs_review = _derive_needs_review(photo, active_design, has_failed_jobs)

        if ai_status and derived_ai_status != ai_status:
            continue
        if design_source and (active_design.source if active_design else None) != design_source:
            continue
        if failed_only and not has_failed_jobs:
            continue
        if needs_review and not derived_needs_review:
            continue

        items.append(
            AdminPhotoListItem(
                id=photo.id,
                owner_id=photo.owner_id,
                category=photo.category,
                final_caption=photo.final_caption,
                user_message=photo.user_message,
                status=photo.status,
                uploaded_at=photo.uploaded_at,
                taken_at=photo.taken_at,
                location_name=photo.location_name,
                location_city=photo.location_city,
                geocoding_status=photo.geocoding_status,
                ai_status=derived_ai_status,
                active_design_source=active_design.source if active_design else None,
                active_design_version=active_design.version if active_design else None,
                latest_job_type=latest_job.job_type if latest_job else None,
                latest_job_status=latest_job.status if latest_job else None,
                latest_job_error=latest_job.error_message if latest_job else None,
                has_failed_jobs=has_failed_jobs,
                needs_review=derived_needs_review,
            )
        )

    total = len(items)
    return items[offset: offset + limit], total
