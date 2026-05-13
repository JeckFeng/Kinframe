"""add v0.2 phase1 data model: location, geocoding, category_source, AI fields, job type expansion

Revision ID: 20260512_0007
Revises: 20260512_0006
Create Date: 2026-05-12
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260512_0007"
down_revision: str | None = "20260512_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── photos: location fields ──────────────────────────────────
    op.add_column("photos", sa.Column("location_name", sa.String(length=300), nullable=True))
    op.add_column("photos", sa.Column("location_country", sa.String(length=100), nullable=True))
    op.add_column("photos", sa.Column("location_region", sa.String(length=200), nullable=True))
    op.add_column("photos", sa.Column("location_city", sa.String(length=200), nullable=True))
    op.add_column("photos", sa.Column("location_district", sa.String(length=200), nullable=True))
    op.add_column("photos", sa.Column("location_road", sa.String(length=300), nullable=True))

    # ── photos: geocoding state ──────────────────────────────────
    op.add_column(
        "photos",
        sa.Column(
            "geocoding_status",
            sa.String(length=30),
            nullable=False,
            server_default="not_applicable",
        ),
    )
    op.add_column("photos", sa.Column("geocoding_provider", sa.String(length=50), nullable=True))
    op.add_column("photos", sa.Column("geocoding_error", sa.Text(), nullable=True))
    op.add_column("photos", sa.Column("geocoded_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f("ix_photos_geocoding_status"), "photos", ["geocoding_status"], unique=False)

    # ── photos: category source ──────────────────────────────────
    op.add_column(
        "photos",
        sa.Column(
            "category_source",
            sa.String(length=20),
            nullable=False,
            server_default="user",
        ),
    )
    op.create_index(op.f("ix_photos_category_source"), "photos", ["category_source"], unique=False)

    # Set category_source for existing rows (they were uploaded with user-chosen category)
    op.execute("UPDATE photos SET category_source = 'user'")

    # ── photos: AI analysis ──────────────────────────────────────
    op.add_column("photos", sa.Column("ai_analysis_json", sa.JSON(), nullable=True))

    # ── photo_processing_jobs: expand job_type and add AI tracking ──
    op.drop_constraint("ck_photo_processing_jobs_job_type", "photo_processing_jobs", type_="check")
    op.create_check_constraint(
        "ck_photo_processing_jobs_job_type",
        "photo_processing_jobs",
        "job_type in ('photo_ingest', 'slide_design_generate', 'reverse_geocode', 'vision_analyze')",
    )
    op.add_column("photo_processing_jobs", sa.Column("ai_provider", sa.String(length=50), nullable=True))
    op.add_column("photo_processing_jobs", sa.Column("ai_model", sa.String(length=100), nullable=True))
    op.add_column("photo_processing_jobs", sa.Column("ai_prompt_version", sa.String(length=30), nullable=True))
    op.add_column("photo_processing_jobs", sa.Column("ai_raw_summary", sa.Text(), nullable=True))


def downgrade() -> None:
    # photo_processing_jobs
    op.drop_column("photo_processing_jobs", "ai_raw_summary")
    op.drop_column("photo_processing_jobs", "ai_prompt_version")
    op.drop_column("photo_processing_jobs", "ai_model")
    op.drop_column("photo_processing_jobs", "ai_provider")
    op.drop_constraint("ck_photo_processing_jobs_job_type", "photo_processing_jobs", type_="check")
    op.create_check_constraint(
        "ck_photo_processing_jobs_job_type",
        "photo_processing_jobs",
        "job_type in ('photo_ingest', 'slide_design_generate')",
    )

    # photos
    op.drop_column("photos", "ai_analysis_json")
    op.drop_index(op.f("ix_photos_category_source"), table_name="photos")
    op.drop_column("photos", "category_source")
    op.drop_index(op.f("ix_photos_geocoding_status"), table_name="photos")
    op.drop_column("photos", "geocoded_at")
    op.drop_column("photos", "geocoding_error")
    op.drop_column("photos", "geocoding_provider")
    op.drop_column("photos", "geocoding_status")
    op.drop_column("photos", "location_road")
    op.drop_column("photos", "location_district")
    op.drop_column("photos", "location_city")
    op.drop_column("photos", "location_region")
    op.drop_column("photos", "location_country")
    op.drop_column("photos", "location_name")
