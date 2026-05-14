"""Schemas for photo APIs."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.slide_design_validator import validate_slide_design_data

PhotoCategory = str  # validated dynamically against categories table


class PhotoCategoryRead(BaseModel):
    """Default category metadata exposed during the PRD transition."""

    id: str
    slug: str
    name: str
    description: str | None
    legacy_slug: str | None
    sort_order: int
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class PhotoPublicRead(BaseModel):
    """Photo metadata returned to regular users (no sensitive diagnostics)."""

    id: str
    owner_id: str
    category: PhotoCategory
    category_source: str
    caption_source: str = "none"
    user_message: str | None
    ai_caption: str | None
    final_caption: str | None
    ai_category_suggestion: str | None
    ai_caption_enabled: bool
    ai_category_enabled: bool
    include_in_showcase: bool
    time_source: str
    bucket: str
    object_key_original: str
    object_key_thumbnail: str
    object_key_preview: str | None
    mime_type: str
    file_size: int
    sha256: str
    width: int | None
    height: int | None
    taken_at: datetime
    uploaded_at: datetime
    gps_lat: float | None
    gps_lng: float | None
    camera_make: str | None
    camera_model: str | None
    location_name: str | None = None
    location_country: str | None = None
    location_region: str | None = None
    location_city: str | None = None
    location_district: str | None = None
    location_road: str | None = None
    geocoding_status: str = "not_applicable"
    geocoding_provider: str | None = None
    geocoded_at: datetime | None = None
    status: str
    processing_message: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PhotoAdminRead(BaseModel):
    """Full photo metadata for admin diagnostics (includes AI raw output, EXIF, errors)."""

    id: str
    owner_id: str
    category: PhotoCategory
    category_source: str
    caption_source: str = "none"
    user_message: str | None
    ai_caption: str | None
    final_caption: str | None
    ai_category_suggestion: str | None
    ai_analysis_json: dict | None = None
    ai_caption_enabled: bool
    ai_category_enabled: bool
    include_in_showcase: bool
    time_source: str
    bucket: str
    object_key_original: str
    object_key_thumbnail: str
    object_key_preview: str | None
    mime_type: str
    file_size: int
    sha256: str
    width: int | None
    height: int | None
    taken_at: datetime
    uploaded_at: datetime
    gps_lat: float | None
    gps_lng: float | None
    camera_make: str | None
    camera_model: str | None
    exif_json: dict | None
    location_name: str | None = None
    location_country: str | None = None
    location_region: str | None = None
    location_city: str | None = None
    location_district: str | None = None
    location_road: str | None = None
    geocoding_status: str = "not_applicable"
    geocoding_provider: str | None = None
    geocoding_error: str | None = None
    geocoded_at: datetime | None = None
    status: str
    processing_message: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Backward-compatible alias: existing endpoints use PhotoRead
PhotoRead = PhotoPublicRead


class PhotoMessageUpdate(BaseModel):
    """Payload for user self-service message editing."""

    user_message: str = Field(..., min_length=1, max_length=2000)


class PhotoUpdate(BaseModel):
    """Editable photo fields for regular users."""

    category: PhotoCategory | None = None
    user_message: str | None = Field(default=None, max_length=2000)
    ai_caption_enabled: bool | None = None
    ai_category_enabled: bool | None = None
    include_in_showcase: bool | None = None


class AdminPhotoUpdate(BaseModel):
    """Editable photo fields for admins (includes location, final_caption)."""

    category: PhotoCategory | None = None
    final_caption: str | None = Field(default=None, max_length=2000)
    location_name: str | None = None
    location_country: str | None = None
    location_region: str | None = None
    location_city: str | None = None
    location_district: str | None = None
    location_road: str | None = None


from typing import Literal


class RegenerateScope(BaseModel):
    """Scope for admin granular photo regeneration."""

    scope: Literal["caption", "template", "css_tokens", "full", "fallback"]


class PresignedUrlResponse(BaseModel):
    """Short-lived object URL response."""

    url: str


class PhotoProcessingStatusResponse(BaseModel):
    """Photo processing state returned for frontend polling."""

    photo_id: str
    photo_status: str
    job_type: str | None
    job_status: str | None
    attempts: int | None
    max_attempts: int | None
    error_message: str | None
    slide_design_status: str | None
    slide_design_source: str | None
    ai_provider: str | None = None
    ai_model: str | None = None
    geocoding_status: str | None = None


class PhotoBatchUploadItem(BaseModel):
    """Per-file batch upload result."""

    filename: str
    success: bool
    photo: PhotoRead | None
    error: str | None


class PhotoBatchUploadResponse(BaseModel):
    """Batch upload response with independent per-file outcomes."""

    success_count: int
    failure_count: int
    results: list[PhotoBatchUploadItem]


class SlideDesignCreate(BaseModel):
    """Payload for storing one slide design version."""

    version: int = Field(ge=1)
    design_json: dict[str, Any]
    source: Literal["fallback", "ai", "manual"]
    status: Literal["draft", "active", "failed"]
    validation_errors: list[str] | None = None

    @field_validator("design_json")
    @classmethod
    def _validate_design_json(cls, value: dict[str, Any]) -> dict[str, Any]:
        return validate_slide_design_data(value)


class SlideDesignRead(BaseModel):
    """Slide design returned by photo APIs."""

    id: str
    photo_id: str
    version: int
    design_json: dict[str, Any]
    source: Literal["fallback", "ai", "manual"]
    status: Literal["draft", "active", "failed"]
    validation_errors: list[str] | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
