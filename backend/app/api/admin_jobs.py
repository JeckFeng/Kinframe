"""Admin job management routes."""

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict

from app.api.deps import DbSession, get_current_admin
from app.models import Photo, PhotoProcessingJob, User
from app.services.audit_logs import create_audit_log
from app.services.photo_jobs import (
    PHOTO_JOB_TYPE_PHOTO_PURGE,
    PHOTO_JOB_STATUS_PENDING,
)
from app.services.photos import get_photo

router = APIRouter(prefix="/api/admin/jobs", tags=["admin-jobs"])


class AdminJobItem(BaseModel):
    """Job with photo metadata for the admin jobs table."""

    id: str
    photo_id: str | None
    job_type: str
    status: str
    attempts: int
    max_attempts: int
    error_message: str | None
    ai_provider: str | None
    ai_model: str | None
    ai_prompt_version: str | None
    ai_raw_summary: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    photo_category: str | None
    photo_status: str | None
    photo_file_size: int | None
    photo_width: int | None
    photo_height: int | None
    photo_taken_at: datetime | None
    photo_user_message: str | None

    model_config = ConfigDict(from_attributes=True)


@router.get("", response_model=list[AdminJobItem])
def get_jobs(
    db: DbSession,
    _admin: Annotated[User, Depends(get_current_admin)],
    photo_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    job_type: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=500),
) -> list[AdminJobItem]:
    """List all processing jobs with photo metadata, newest first."""

    from sqlalchemy import select

    stmt = (
        select(PhotoProcessingJob, Photo)
        .outerjoin(Photo, PhotoProcessingJob.photo_id == Photo.id)
        .order_by(PhotoProcessingJob.created_at.desc())
    )
    if photo_id:
        stmt = stmt.where(PhotoProcessingJob.photo_id == photo_id)
    if status:
        stmt = stmt.where(PhotoProcessingJob.status == status)
    if job_type:
        stmt = stmt.where(PhotoProcessingJob.job_type == job_type)
    stmt = stmt.limit(limit)

    rows = db.execute(stmt).all()

    return [
        AdminJobItem(
            id=job.id,
            photo_id=job.photo_id,
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
            photo_category=photo.category if photo is not None else None,
            photo_status=photo.status if photo is not None else None,
            photo_file_size=photo.file_size if photo is not None else None,
            photo_width=photo.width if photo is not None else None,
            photo_height=photo.height if photo is not None else None,
            photo_taken_at=photo.taken_at if photo is not None else None,
            photo_user_message=photo.user_message if photo is not None else None,
        )
        for job, photo in rows
    ]


@router.post("/{job_id}/retry", status_code=status.HTTP_200_OK)
def retry_job(
    job_id: str,
    db: DbSession,
    admin: Annotated[User, Depends(get_current_admin)],
) -> dict:
    """Retry a failed job by resetting it to pending."""

    job = db.get(PhotoProcessingJob, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job.status not in ("failed", "succeeded"):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Job is not in a retryable state")

    now = datetime.now(timezone.utc)
    job.status = PHOTO_JOB_STATUS_PENDING
    job.error_message = None
    job.started_at = None
    job.finished_at = None
    job.updated_at = now
    db.add(job)

    photo = get_photo(db, job.photo_id) if job.photo_id is not None else None
    if photo is not None and job.job_type != PHOTO_JOB_TYPE_PHOTO_PURGE:
        photo.status = "processing"
        photo.updated_at = now
        db.add(photo)

    db.commit()
    create_audit_log(
        db,
        admin_id=admin.id,
        action="job.retry",
        target_type="job",
        target_id=job.id,
        detail={
            "job_type": job.job_type,
            "photo_id": job.photo_id,
            "summary": f"Admin {admin.username} reset job to pending",
        },
    )
    return {"message": "Job reset to pending"}
