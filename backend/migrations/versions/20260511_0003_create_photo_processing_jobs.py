"""create photo processing jobs table

Revision ID: 20260511_0003
Revises: 20260511_0002
Create Date: 2026-05-11
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260511_0003"
down_revision: str | None = "20260511_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("update photos set status = 'ready' where status = 'confirmed'")
    op.create_table(
        "photo_processing_jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("photo_id", sa.String(length=36), nullable=False),
        sa.Column("job_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status in ('pending', 'running', 'succeeded', 'failed')",
            name="ck_photo_processing_jobs_status",
        ),
        sa.ForeignKeyConstraint(["photo_id"], ["photos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_photo_processing_jobs_job_type"), "photo_processing_jobs", ["job_type"], unique=False)
    op.create_index(op.f("ix_photo_processing_jobs_photo_id"), "photo_processing_jobs", ["photo_id"], unique=False)
    op.create_index(op.f("ix_photo_processing_jobs_status"), "photo_processing_jobs", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_photo_processing_jobs_status"), table_name="photo_processing_jobs")
    op.drop_index(op.f("ix_photo_processing_jobs_photo_id"), table_name="photo_processing_jobs")
    op.drop_index(op.f("ix_photo_processing_jobs_job_type"), table_name="photo_processing_jobs")
    op.drop_table("photo_processing_jobs")
    op.execute("update photos set status = 'confirmed' where status = 'ready'")
