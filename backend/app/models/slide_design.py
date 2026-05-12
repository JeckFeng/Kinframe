"""Slide design ORM model."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def utc_now() -> datetime:
    """Return the current UTC timestamp."""

    return datetime.now(timezone.utc)


class SlideDesign(Base):
    """Structured render data for one photo slide."""

    __tablename__ = "slide_designs"
    __table_args__ = (
        CheckConstraint("version >= 1", name="ck_slide_designs_version_positive"),
        CheckConstraint("status in ('draft', 'active', 'failed')", name="ck_slide_designs_status"),
        CheckConstraint("source in ('fallback', 'ai', 'manual')", name="ck_slide_designs_source"),
        UniqueConstraint("photo_id", "version", name="uq_slide_designs_photo_version"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    photo_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("photos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    design_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    source: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    validation_errors: Mapped[list[str] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )
