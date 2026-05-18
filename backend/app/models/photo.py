"""Photo ORM model."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def utc_now() -> datetime:
    """Return the current UTC timestamp."""

    return datetime.now(timezone.utc)


class Photo(Base):
    """Uploaded family photo metadata."""

    __tablename__ = "photos"
    __table_args__ = (
        CheckConstraint("category in ('life', 'travel', 'photography', 'pet')", name="ck_photos_category"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    owner_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    category_source: Mapped[str] = mapped_column(
        String(50), nullable=False, default="user", index=True,
    )
    caption_source: Mapped[str] = mapped_column(
        String(20), nullable=False, default="none", index=True,
    )
    user_message: Mapped[str | None] = mapped_column(Text())
    final_caption: Mapped[str | None] = mapped_column(Text())
    include_in_showcase: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    time_source: Mapped[str] = mapped_column(String(30), nullable=False, default="uploaded_at")
    bucket: Mapped[str] = mapped_column(String(100), nullable=False)
    object_key_original: Mapped[str] = mapped_column(String(500), nullable=False)
    object_key_thumbnail: Mapped[str] = mapped_column(String(500), nullable=False)
    object_key_preview: Mapped[str | None] = mapped_column(String(500))
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    taken_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    gps_lat: Mapped[float | None] = mapped_column(Float)
    gps_lng: Mapped[float | None] = mapped_column(Float)
    camera_make: Mapped[str | None] = mapped_column(String(100))
    camera_model: Mapped[str | None] = mapped_column(String(100))
    exif_json: Mapped[dict | None] = mapped_column(JSON)
    # Reverse geocoding
    location_name: Mapped[str | None] = mapped_column(String(300))
    location_country: Mapped[str | None] = mapped_column(String(100))
    location_region: Mapped[str | None] = mapped_column(String(200))
    location_city: Mapped[str | None] = mapped_column(String(200))
    location_district: Mapped[str | None] = mapped_column(String(200))
    location_road: Mapped[str | None] = mapped_column(String(300))
    geocoding_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="not_applicable", index=True,
    )
    geocoding_provider: Mapped[str | None] = mapped_column(String(50))
    geocoding_error: Mapped[str | None] = mapped_column(Text())
    geocoded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="confirmed", index=True)
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
