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
    active_design_source: Literal["fallback", "ai", "manual"] | None = None
    active_design_version: int | None = None
    latest_job_type: str | None = None
    latest_job_status: str | None = None
    latest_job_error: str | None = None
    ai_status: Literal["missing", "analyzed", "failed"] = "missing"
    has_failed_jobs: bool = False
    needs_review: bool = False
    design_versions: list["SlideDesignSummaryRead"] = Field(default_factory=list)
    recent_jobs: list["AdminPhotoJobRead"] = Field(default_factory=list)
    recent_audit_logs: list["AdminAuditLogRead"] = Field(default_factory=list)
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


class ManualSlideDesignCreate(BaseModel):
    """Payload for storing a manual slide design draft or active version."""

    design_json: dict[str, Any]
    activate: bool = False


class MapPhotoItem(BaseModel):
    """Single photo record for map marker rendering."""

    photo_id: str
    preview_url: str
    thumbnail_url: str
    category: str
    gps_lat: float
    gps_lng: float
    location_name: str | None = None
    location_city: str | None = None
    location_region: str | None = None
    location_country: str | None = None
    location_district: str | None = None
    final_caption: str | None = None
    taken_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class MapPhotosResponse(BaseModel):
    """Response wrapper for map photo list."""

    photos: list[MapPhotoItem]


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


class QualityReportRead(BaseModel):
    total_score: int
    passed: bool
    failures: list[str] = Field(default_factory=list)


class SlideDesignSummaryRead(BaseModel):
    id: str
    version: int
    source: Literal["fallback", "ai", "manual"]
    status: Literal["draft", "active", "failed"]
    design_json: dict[str, Any] | None = None
    template_id: str | None = None
    layer_count: int = 0
    quality_report: QualityReportRead | None = None
    validation_errors: list[str] | None = None
    created_at: datetime
    updated_at: datetime


class AdminPhotoJobRead(BaseModel):
    id: str
    job_type: str
    status: str
    attempts: int
    max_attempts: int
    error_message: str | None = None
    ai_provider: str | None = None
    ai_model: str | None = None
    ai_prompt_version: str | None = None
    ai_raw_summary: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime


class AdminAuditLogRead(BaseModel):
    id: str
    action: str
    target_type: str
    target_id: str | None = None
    summary: str | None = None
    detail: dict | None = None
    created_at: datetime


class AdminPhotoListItem(BaseModel):
    id: str
    owner_id: str
    category: PhotoCategory
    final_caption: str | None = None
    user_message: str | None = None
    include_in_showcase: bool
    status: str
    uploaded_at: datetime
    taken_at: datetime
    location_name: str | None = None
    location_city: str | None = None
    geocoding_status: str = "not_applicable"
    ai_status: Literal["missing", "analyzed", "failed"] = "missing"
    active_design_source: Literal["fallback", "ai", "manual"] | None = None
    active_design_version: int | None = None
    latest_job_type: str | None = None
    latest_job_status: str | None = None
    latest_job_error: str | None = None
    has_failed_jobs: bool = False
    needs_review: bool = False


class AdminPhotoListResponse(BaseModel):
    items: list[AdminPhotoListItem]
    total: int
    limit: int
    offset: int

    model_config = ConfigDict(from_attributes=True)
