"""add v0.2 phase6 data model: caption_source, audit_logs, widen category_source

Revision ID: 20260513_0008
Revises: 20260512_0007
Create Date: 2026-05-13
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260513_0008"
down_revision: str | None = "20260512_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── photos: widen category_source for admin:username format ────
    op.alter_column("photos", "category_source", type_=sa.String(length=50), existing_type=sa.String(length=20), existing_nullable=False, existing_server_default="user")

    # ── photos: caption_source ─────────────────────────────────────
    op.add_column(
        "photos",
        sa.Column(
            "caption_source",
            sa.String(length=20),
            nullable=False,
            server_default="none",
        ),
    )
    op.create_index(op.f("ix_photos_caption_source"), "photos", ["caption_source"], unique=False)

    # Set caption_source based on existing data
    op.execute("UPDATE photos SET caption_source = 'user' WHERE user_message IS NOT NULL AND user_message != ''")
    op.execute("UPDATE photos SET caption_source = 'ai' WHERE ai_caption IS NOT NULL AND (user_message IS NULL OR user_message = '')")

    # ── audit_logs ──────────────────────────────────────────────────
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("admin_id", sa.String(length=36), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("target_type", sa.String(length=50), nullable=False),
        sa.Column("target_id", sa.String(length=36), nullable=True),
        sa.Column("detail", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["admin_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_logs_admin_id"), "audit_logs", ["admin_id"], unique=False)
    op.create_index(op.f("ix_audit_logs_action"), "audit_logs", ["action"], unique=False)
    op.create_index(op.f("ix_audit_logs_target_type"), "audit_logs", ["target_type"], unique=False)
    op.create_index(op.f("ix_audit_logs_target_id"), "audit_logs", ["target_id"], unique=False)
    op.create_index(op.f("ix_audit_logs_created_at"), "audit_logs", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_index(op.f("ix_photos_caption_source"), table_name="photos")
    op.drop_column("photos", "caption_source")
    op.alter_column("photos", "category_source", type_=sa.String(length=20), existing_type=sa.String(length=50), existing_nullable=False, existing_server_default="user")
