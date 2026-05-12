"""create photos table

Revision ID: 20260511_0002
Revises: 20260511_0001
Create Date: 2026-05-11
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260511_0002"
down_revision: str | None = "20260511_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "photos",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("owner_id", sa.String(length=36), nullable=False),
        sa.Column("category", sa.String(length=20), nullable=False),
        sa.Column("user_message", sa.Text(), nullable=True),
        sa.Column("final_caption", sa.Text(), nullable=True),
        sa.Column("bucket", sa.String(length=100), nullable=False),
        sa.Column("object_key_original", sa.String(length=500), nullable=False),
        sa.Column("object_key_thumbnail", sa.String(length=500), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("taken_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("gps_lat", sa.Float(), nullable=True),
        sa.Column("gps_lng", sa.Float(), nullable=True),
        sa.Column("camera_make", sa.String(length=100), nullable=True),
        sa.Column("camera_model", sa.String(length=100), nullable=True),
        sa.Column("exif_json", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("category in ('life', 'travel', 'pet')", name="ck_photos_category"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_photos_category"), "photos", ["category"], unique=False)
    op.create_index(op.f("ix_photos_owner_id"), "photos", ["owner_id"], unique=False)
    op.create_index(op.f("ix_photos_sha256"), "photos", ["sha256"], unique=True)
    op.create_index(op.f("ix_photos_status"), "photos", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_photos_status"), table_name="photos")
    op.drop_index(op.f("ix_photos_sha256"), table_name="photos")
    op.drop_index(op.f("ix_photos_owner_id"), table_name="photos")
    op.drop_index(op.f("ix_photos_category"), table_name="photos")
    op.drop_table("photos")
