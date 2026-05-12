"""add photo preview object key

Revision ID: 20260511_0004
Revises: 20260511_0003
Create Date: 2026-05-11
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260511_0004"
down_revision: str | None = "20260511_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("photos", sa.Column("object_key_preview", sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column("photos", "object_key_preview")
