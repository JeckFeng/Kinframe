"""make photo_processing_jobs photo link nullable and preserve jobs on photo delete

Revision ID: 20260516_0010
Revises: 20260516_0009
Create Date: 2026-05-16
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260516_0010"
down_revision: str | None = "20260516_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("photo_processing_jobs") as batch_op:
        batch_op.drop_constraint("photo_processing_jobs_photo_id_fkey", type_="foreignkey")
        batch_op.alter_column("photo_id", existing_type=sa.String(length=36), nullable=True)
        batch_op.create_foreign_key(
            "photo_processing_jobs_photo_id_fkey",
            "photos",
            ["photo_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("photo_processing_jobs") as batch_op:
        batch_op.drop_constraint("photo_processing_jobs_photo_id_fkey", type_="foreignkey")
        batch_op.alter_column("photo_id", existing_type=sa.String(length=36), nullable=False)
        batch_op.create_foreign_key(
            "photo_processing_jobs_photo_id_fkey",
            "photos",
            ["photo_id"],
            ["id"],
            ondelete="CASCADE",
        )
