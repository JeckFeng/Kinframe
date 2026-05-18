"""remove ai features

Revision ID: 20260516_0011
Revises: 20260516_0010
Create Date: 2026-05-16
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260516_0011"
down_revision: str | None = "20260516_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


LEGACY_AI_JOB_TYPES = (
    "vision_analyze",
    "slide_design_generate",
    "caption_regenerate",
    "template_regenerate",
    "css_regenerate",
)


def upgrade() -> None:
    op.execute(
        """
        UPDATE photos
        SET final_caption = CASE
                WHEN user_message IS NOT NULL AND user_message <> '' THEN user_message
                ELSE NULL
            END,
            caption_source = CASE
                WHEN user_message IS NOT NULL AND user_message <> '' THEN 'user'
                ELSE 'none'
            END
        WHERE caption_source = 'ai'
        """
    )
    op.execute("UPDATE photos SET category_source = 'fallback' WHERE category_source = 'ai'")
    op.execute("DELETE FROM slide_designs WHERE source = 'ai'")
    op.execute(
        "DELETE FROM photo_processing_jobs WHERE job_type IN ('vision_analyze', 'slide_design_generate', 'caption_regenerate', 'template_regenerate', 'css_regenerate')"
    )

    op.drop_constraint("ck_slide_designs_source", "slide_designs", type_="check")
    op.create_check_constraint(
        "ck_slide_designs_source",
        "slide_designs",
        "source in ('fallback', 'manual')",
    )

    op.drop_constraint("ck_photo_processing_jobs_job_type", "photo_processing_jobs", type_="check")
    op.create_check_constraint(
        "ck_photo_processing_jobs_job_type",
        "photo_processing_jobs",
        "job_type in ('photo_ingest', 'reverse_geocode', 'fallback_regenerate', 'photo_purge')",
    )

    op.drop_column("photo_processing_jobs", "ai_raw_summary")
    op.drop_column("photo_processing_jobs", "ai_prompt_version")
    op.drop_column("photo_processing_jobs", "ai_model")
    op.drop_column("photo_processing_jobs", "ai_provider")

    op.drop_column("photos", "ai_category_enabled")
    op.drop_column("photos", "ai_caption_enabled")
    op.drop_column("photos", "ai_analysis_json")
    op.drop_column("photos", "ai_category_suggestion")
    op.drop_column("photos", "ai_caption")


def downgrade() -> None:
    op.add_column("photos", sa.Column("ai_caption", sa.Text(), nullable=True))
    op.add_column("photos", sa.Column("ai_category_suggestion", sa.String(length=50), nullable=True))
    op.add_column("photos", sa.Column("ai_analysis_json", sa.JSON(), nullable=True))
    op.add_column(
        "photos",
        sa.Column("ai_caption_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "photos",
        sa.Column("ai_category_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )

    op.add_column("photo_processing_jobs", sa.Column("ai_provider", sa.String(length=50), nullable=True))
    op.add_column("photo_processing_jobs", sa.Column("ai_model", sa.String(length=100), nullable=True))
    op.add_column("photo_processing_jobs", sa.Column("ai_prompt_version", sa.String(length=30), nullable=True))
    op.add_column("photo_processing_jobs", sa.Column("ai_raw_summary", sa.Text(), nullable=True))

    op.drop_constraint("ck_photo_processing_jobs_job_type", "photo_processing_jobs", type_="check")
    op.create_check_constraint(
        "ck_photo_processing_jobs_job_type",
        "photo_processing_jobs",
        "job_type in ('photo_ingest', 'slide_design_generate', 'reverse_geocode', 'vision_analyze', 'caption_regenerate', 'template_regenerate', 'css_regenerate', 'fallback_regenerate', 'photo_purge')",
    )

    op.drop_constraint("ck_slide_designs_source", "slide_designs", type_="check")
    op.create_check_constraint(
        "ck_slide_designs_source",
        "slide_designs",
        "source in ('fallback', 'ai', 'manual')",
    )
