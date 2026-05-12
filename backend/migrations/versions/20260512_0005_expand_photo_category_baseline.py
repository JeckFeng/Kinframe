"""expand photo category baseline for PRD transition

Revision ID: 20260512_0005
Revises: 20260511_0004
Create Date: 2026-05-12
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260512_0005"
down_revision: str | None = "20260511_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.drop_constraint("ck_photos_category", "photos", type_="check")
        op.create_check_constraint(
            "ck_photos_category",
            "photos",
            "category in ('life', 'travel', 'photography', 'pet')",
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("update photos set category = 'travel' where category = 'photography'")
        op.drop_constraint("ck_photos_category", "photos", type_="check")
        op.create_check_constraint(
            "ck_photos_category",
            "photos",
            "category in ('life', 'travel', 'pet')",
        )
