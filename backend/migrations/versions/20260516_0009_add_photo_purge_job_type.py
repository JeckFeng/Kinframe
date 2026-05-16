"""add photo_purge job type

Revision ID: 20260516_0009
Revises: 20260513_0008
Create Date: 2026-05-16
"""

from collections.abc import Sequence

from alembic import op


revision: str = "20260516_0009"
down_revision: str | None = "20260513_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("ck_photo_processing_jobs_job_type", "photo_processing_jobs", type_="check")
    op.create_check_constraint(
        "ck_photo_processing_jobs_job_type",
        "photo_processing_jobs",
        "job_type in ('photo_ingest', 'slide_design_generate', 'reverse_geocode', 'vision_analyze', 'caption_regenerate', 'template_regenerate', 'css_regenerate', 'fallback_regenerate', 'photo_purge')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_photo_processing_jobs_job_type", "photo_processing_jobs", type_="check")
    op.create_check_constraint(
        "ck_photo_processing_jobs_job_type",
        "photo_processing_jobs",
        "job_type in ('photo_ingest', 'slide_design_generate', 'reverse_geocode', 'vision_analyze', 'caption_regenerate', 'template_regenerate', 'css_regenerate', 'fallback_regenerate')",
    )
