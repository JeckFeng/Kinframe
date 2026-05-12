"""add PRD data model tables and fields

Revision ID: 20260512_0006
Revises: 20260512_0005
Create Date: 2026-05-12
"""

from collections.abc import Sequence
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision: str = "20260512_0006"
down_revision: str | None = "20260512_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    now = datetime.now(timezone.utc)
    op.create_table(
        "categories",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("slug", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("legacy_slug", sa.String(length=50), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("legacy_slug"),
    )
    op.create_index(op.f("ix_categories_slug"), "categories", ["slug"], unique=True)
    op.bulk_insert(
        sa.table(
            "categories",
            sa.column("id", sa.String),
            sa.column("slug", sa.String),
            sa.column("name", sa.String),
            sa.column("description", sa.Text),
            sa.column("legacy_slug", sa.String),
            sa.column("sort_order", sa.Integer),
            sa.column("is_active", sa.Boolean),
            sa.column("created_at", sa.DateTime(timezone=True)),
            sa.column("updated_at", sa.DateTime(timezone=True)),
        ),
        [
            {
                "id": "00000000-0000-0000-0000-000000000101",
                "slug": "life",
                "name": "生活照",
                "description": "家庭日常、聚会和普通生活记录",
                "legacy_slug": None,
                "sort_order": 10,
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            },
            {
                "id": "00000000-0000-0000-0000-000000000102",
                "slug": "photography",
                "name": "摄影照",
                "description": "更偏摄影作品、旅行风景和构图记录",
                "legacy_slug": "travel",
                "sort_order": 20,
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            },
            {
                "id": "00000000-0000-0000-0000-000000000103",
                "slug": "pet",
                "name": "宠物照",
                "description": "家庭宠物和动物陪伴记录",
                "legacy_slug": None,
                "sort_order": 30,
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            },
        ],
    )
    op.add_column("photos", sa.Column("ai_caption", sa.Text(), nullable=True))
    op.add_column("photos", sa.Column("ai_category_suggestion", sa.String(length=50), nullable=True))
    op.add_column(
        "photos",
        sa.Column("ai_caption_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "photos",
        sa.Column("ai_category_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "photos",
        sa.Column("include_in_showcase", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.add_column(
        "photos",
        sa.Column("time_source", sa.String(length=30), nullable=False, server_default="uploaded_at"),
    )
    op.create_index(op.f("ix_photos_include_in_showcase"), "photos", ["include_in_showcase"], unique=False)
    op.create_table(
        "slide_designs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("photo_id", sa.String(length=36), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("design_json", sa.JSON(), nullable=False),
        sa.Column("source", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("validation_errors", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("version >= 1", name="ck_slide_designs_version_positive"),
        sa.CheckConstraint("status in ('draft', 'active', 'failed')", name="ck_slide_designs_status"),
        sa.CheckConstraint("source in ('fallback', 'ai', 'manual')", name="ck_slide_designs_source"),
        sa.ForeignKeyConstraint(["photo_id"], ["photos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("photo_id", "version", name="uq_slide_designs_photo_version"),
    )
    op.create_index(op.f("ix_slide_designs_photo_id"), "slide_designs", ["photo_id"], unique=False)
    op.create_index(op.f("ix_slide_designs_source"), "slide_designs", ["source"], unique=False)
    op.create_index(op.f("ix_slide_designs_status"), "slide_designs", ["status"], unique=False)
    op.execute("update photo_processing_jobs set job_type = 'photo_ingest' where job_type = 'metadata_thumbnail'")
    op.create_check_constraint(
        "ck_photo_processing_jobs_job_type",
        "photo_processing_jobs",
        "job_type in ('photo_ingest', 'slide_design_generate')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_photo_processing_jobs_job_type", "photo_processing_jobs", type_="check")
    op.execute("update photo_processing_jobs set job_type = 'metadata_thumbnail' where job_type = 'photo_ingest'")
    op.drop_index(op.f("ix_slide_designs_status"), table_name="slide_designs")
    op.drop_index(op.f("ix_slide_designs_source"), table_name="slide_designs")
    op.drop_index(op.f("ix_slide_designs_photo_id"), table_name="slide_designs")
    op.drop_table("slide_designs")
    op.drop_index(op.f("ix_photos_include_in_showcase"), table_name="photos")
    op.drop_column("photos", "time_source")
    op.drop_column("photos", "include_in_showcase")
    op.drop_column("photos", "ai_category_enabled")
    op.drop_column("photos", "ai_caption_enabled")
    op.drop_column("photos", "ai_category_suggestion")
    op.drop_column("photos", "ai_caption")
    op.drop_index(op.f("ix_categories_slug"), table_name="categories")
    op.drop_table("categories")
