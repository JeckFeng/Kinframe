"""Admin job management routes."""

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict

from app.api.deps import DbSession, get_current_admin
from app.models import Photo, PhotoProcessingJob, User
from app.services.photo_jobs import (
    PHOTO_JOB_STATUS_PENDING,
    get_latest_job_for_photo,
)
from app.services.photos import get_photo

router = APIRouter(prefix="/api/admin/jobs", tags=["admin-jobs"])


class AdminJobItem(BaseModel):
    """Job with photo metadata for the admin jobs table."""

    id: str
    photo_id: str
    job_type: str
    status: str
    attempts: int
    max_attempts: int
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    photo_category: str
    photo_status: str
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
) -> list[AdminJobItem]:
    """List all processing jobs with photo metadata, newest first."""

    from sqlalchemy import select

    rows = db.execute(
        select(PhotoProcessingJob, Photo)
        .join(Photo, PhotoProcessingJob.photo_id == Photo.id)
        .order_by(PhotoProcessingJob.created_at.desc())
        .limit(200)
    ).all()

    return [
        AdminJobItem(
            id=job.id,
            photo_id=job.photo_id,
            job_type=job.job_type,
            status=job.status,
            attempts=job.attempts,
            max_attempts=job.max_attempts,
            error_message=job.error_message,
            started_at=job.started_at,
            finished_at=job.finished_at,
            created_at=job.created_at,
            photo_category=photo.category,
            photo_status=photo.status,
            photo_file_size=photo.file_size,
            photo_width=photo.width,
            photo_height=photo.height,
            photo_taken_at=photo.taken_at,
            photo_user_message=photo.user_message,
        )
        for job, photo in rows
    ]


@router.post("/{job_id}/retry", status_code=status.HTTP_200_OK)
def retry_job(
    job_id: str,
    db: DbSession,
    _admin: Annotated[User, Depends(get_current_admin)],
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

    photo = get_photo(db, job.photo_id)
    if photo is not None:
        photo.status = "processing"
        photo.updated_at = now
        db.add(photo)

    db.commit()
    return {"message": "Job reset to pending"}
