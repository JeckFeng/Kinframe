"""Photo processing job persistence helpers."""

from datetime import datetime, timezone
from pathlib import Path
from copy import deepcopy

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Photo, PhotoProcessingJob
from app.services.exif import ExtractedMetadata, extract_metadata
from app.services.fallback_slide_design import build_fallback_slide_design
from app.services.geocoding import GeocodingResult, GeocodingService
from app.services.images import generate_preview, generate_thumbnail
from app.services.photos import (
    PHOTO_STATUS_DESIGN_GENERATED,
    PHOTO_STATUS_EXIF_PARSED,
    PHOTO_STATUS_FAILED,
    PHOTO_STATUS_PREVIEW_GENERATED,
    PHOTO_STATUS_PROCESSING,
    PHOTO_STATUS_READY,
    compute_final_caption,
)
from app.services.slide_designs import (
    create_slide_design,
    get_latest_active_slide_design,
    get_latest_slide_design_version,
)
from app.services.storage import ObjectStorage
from app.schemas.photo import SlideDesignCreate
from app.schemas.slide_design_assets import get_template_definition

PHOTO_JOB_TYPE_PHOTO_INGEST = "photo_ingest"
PHOTO_JOB_TYPE_SLIDE_DESIGN_GENERATE = "slide_design_generate"
PHOTO_JOB_TYPE_REVERSE_GEOCODE = "reverse_geocode"
PHOTO_JOB_TYPE_VISION_ANALYZE = "vision_analyze"
PHOTO_JOB_TYPE_CAPTION_REGENERATE = "caption_regenerate"
PHOTO_JOB_TYPE_TEMPLATE_REGENERATE = "template_regenerate"
PHOTO_JOB_TYPE_CSS_REGENERATE = "css_regenerate"
PHOTO_JOB_TYPE_FALLBACK_REGENERATE = "fallback_regenerate"
PHOTO_JOB_TYPE_METADATA_THUMBNAIL = PHOTO_JOB_TYPE_PHOTO_INGEST
PHOTO_JOB_STATUS_PENDING = "pending"
PHOTO_JOB_STATUS_RUNNING = "running"
PHOTO_JOB_STATUS_SUCCEEDED = "succeeded"
PHOTO_JOB_STATUS_FAILED = "failed"
AI_CATEGORY_SLUGS = {"life", "travel", "photography", "pet"}


class PhotoJobCreateError(ValueError):
    """Raised when photo and processing job creation fails."""


def utc_now() -> datetime:
    """Return the current UTC timestamp."""

    return datetime.now(timezone.utc)


def create_photo_with_processing_job(
    db: Session,
    photo: Photo,
    *,
    max_attempts: int,
) -> tuple[Photo, PhotoProcessingJob]:
    """Persist a photo and its initial processing job atomically."""

    job = PhotoProcessingJob(
        photo_id=photo.id,
        job_type=PHOTO_JOB_TYPE_METADATA_THUMBNAIL,
        status=PHOTO_JOB_STATUS_PENDING,
        attempts=0,
        max_attempts=max_attempts,
    )
    db.add(photo)
    db.add(job)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise PhotoJobCreateError(photo.sha256) from exc
    db.refresh(photo)
    db.refresh(job)
    return photo, job


def get_latest_job_for_photo(db: Session, photo_id: str) -> PhotoProcessingJob | None:
    """Return the newest processing job for a photo."""

    return db.scalar(
        select(PhotoProcessingJob)
        .where(PhotoProcessingJob.photo_id == photo_id)
        .order_by(PhotoProcessingJob.created_at.desc(), PhotoProcessingJob.id.desc())
    )


def claim_next_pending_job(db: Session) -> PhotoProcessingJob | None:
    """Claim the oldest pending job for this worker."""

    job = db.scalar(
        select(PhotoProcessingJob)
        .where(
            PhotoProcessingJob.status == PHOTO_JOB_STATUS_PENDING,
            PhotoProcessingJob.attempts < PhotoProcessingJob.max_attempts,
        )
        .order_by(PhotoProcessingJob.created_at.asc(), PhotoProcessingJob.id.asc())
        .with_for_update(skip_locked=True)
    )
    if job is None:
        return None

    now = utc_now()
    job.status = PHOTO_JOB_STATUS_RUNNING
    job.attempts += 1
    job.started_at = now
    job.updated_at = now
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def mark_job_succeeded(
    db: Session,
    job: PhotoProcessingJob,
    photo: Photo,
    metadata: ExtractedMetadata,
) -> None:
    """Mark a job succeeded and publish processed photo metadata."""

    now = utc_now()
    photo.width = metadata.width
    photo.height = metadata.height
    photo.taken_at = metadata.taken_at
    photo.gps_lat = metadata.gps_lat
    photo.gps_lng = metadata.gps_lng
    photo.camera_make = metadata.camera_make
    photo.camera_model = metadata.camera_model
    photo.exif_json = metadata.exif_json
    photo.status = PHOTO_STATUS_READY
    photo.updated_at = now
    job.status = PHOTO_JOB_STATUS_SUCCEEDED
    job.error_message = None
    job.finished_at = now
    job.updated_at = now
    db.add(photo)
    db.add(job)
    db.commit()


def mark_job_failed(
    db: Session,
    job: PhotoProcessingJob,
    photo: Photo | None,
    error_message: str,
) -> None:
    """Record a processing failure and retry until attempts are exhausted."""

    now = utc_now()
    if job.attempts >= job.max_attempts:
        job.status = PHOTO_JOB_STATUS_FAILED
        job.finished_at = now
        if photo is not None:
            photo.status = PHOTO_STATUS_FAILED
            photo.updated_at = now
            db.add(photo)
    else:
        job.status = PHOTO_JOB_STATUS_PENDING
        job.finished_at = None
        if photo is not None:
            photo.status = PHOTO_STATUS_PROCESSING
            photo.updated_at = now
            db.add(photo)
    job.error_message = error_message[:2000]
    job.updated_at = now
    db.add(job)
    db.commit()


def mark_geocode_job_succeeded(
    db: Session,
    job: PhotoProcessingJob,
    photo: Photo,
    result: GeocodingResult,
    provider_name: str,
) -> None:
    """Write location fields and mark geocoding done. Photo status unchanged."""

    now = utc_now()
    photo.location_name = result.name
    photo.location_country = result.country
    photo.location_region = result.region
    photo.location_city = result.city
    photo.location_district = result.district
    photo.location_road = result.road
    photo.geocoding_status = "succeeded"
    photo.geocoding_provider = provider_name
    photo.geocoding_error = None
    photo.geocoded_at = now
    photo.updated_at = now
    job.status = PHOTO_JOB_STATUS_SUCCEEDED
    job.error_message = None
    job.finished_at = now
    job.updated_at = now
    db.add(photo)
    db.add(job)
    db.commit()


def mark_geocode_job_failed(
    db: Session,
    job: PhotoProcessingJob,
    photo: Photo | None,
    error_message: str,
) -> None:
    """Record geocoding failure. Photo status UNCHANGED (stays ready)."""

    now = utc_now()
    if job.attempts >= job.max_attempts:
        job.status = PHOTO_JOB_STATUS_FAILED
        job.finished_at = now
        if photo is not None:
            photo.geocoding_status = "failed"
            photo.geocoding_error = error_message[:2000]
            photo.updated_at = now
            db.add(photo)
    else:
        job.status = PHOTO_JOB_STATUS_PENDING
        job.finished_at = None
    job.error_message = error_message[:2000]
    job.updated_at = now
    db.add(job)
    db.commit()


def create_reverse_geocode_job(
    db: Session,
    photo_id: str,
    *,
    max_attempts: int,
    provider_name: str,
) -> PhotoProcessingJob:
    """Enqueue a reverse-geocoding follow-on job after a successful ingest."""
    existing = _has_pending_or_running_job(db, photo_id, PHOTO_JOB_TYPE_REVERSE_GEOCODE)
    if existing is not None:
        return existing
    job = PhotoProcessingJob(
        photo_id=photo_id,
        job_type=PHOTO_JOB_TYPE_REVERSE_GEOCODE,
        status=PHOTO_JOB_STATUS_PENDING,
        attempts=0,
        max_attempts=max_attempts,
    )
    photo = db.get(Photo, photo_id)
    if photo is not None:
        photo.geocoding_status = "pending"
        photo.geocoding_provider = provider_name
        photo.updated_at = utc_now()
        db.add(photo)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def _has_pending_or_running_job(db: Session, photo_id: str, job_type: str) -> PhotoProcessingJob | None:
    """Return an existing pending/running job of the given type, or None."""
    return db.scalar(
        select(PhotoProcessingJob)
        .where(
            PhotoProcessingJob.photo_id == photo_id,
            PhotoProcessingJob.job_type == job_type,
            PhotoProcessingJob.status.in_([PHOTO_JOB_STATUS_PENDING, PHOTO_JOB_STATUS_RUNNING]),
        )
    )


def create_next_job(
    db: Session,
    photo_id: str,
    *,
    job_type: str,
    max_attempts: int,
    **kwargs: str,
) -> PhotoProcessingJob:
    """Enqueue a follow-on job with duplicate protection. Returns existing if found."""
    existing = _has_pending_or_running_job(db, photo_id, job_type)
    if existing is not None:
        return existing
    job = PhotoProcessingJob(
        photo_id=photo_id,
        job_type=job_type,
        status=PHOTO_JOB_STATUS_PENDING,
        attempts=0,
        max_attempts=max_attempts,
        ai_provider=kwargs.get("provider_name"),
        ai_model=kwargs.get("model"),
        ai_prompt_version=kwargs.get("prompt_version"),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def create_vision_analyze_job(
    db: Session,
    photo_id: str,
    *,
    max_attempts: int,
) -> PhotoProcessingJob:
    """Enqueue a vision_analyze job (with dedup)."""
    from app.core.config import get_settings

    settings = get_settings()
    return create_next_job(
        db,
        photo_id,
        job_type=PHOTO_JOB_TYPE_VISION_ANALYZE,
        max_attempts=max_attempts,
        provider_name="ollama",
        model=settings.ollama_vision_model or "",
    )


def create_slide_design_generate_job(
    db: Session,
    photo_id: str,
    *,
    max_attempts: int,
    provider_name: str,
) -> PhotoProcessingJob:
    """Enqueue a slide_design_generate job (with dedup)."""
    from app.core.config import get_settings

    settings = get_settings()
    return create_next_job(
        db,
        photo_id,
        job_type=PHOTO_JOB_TYPE_SLIDE_DESIGN_GENERATE,
        max_attempts=max_attempts,
        provider_name=provider_name,
        model=settings.deepseek_model or "",
        prompt_version="slide_design.v1",
    )


def create_caption_regenerate_job(
    db: Session,
    photo_id: str,
    *,
    max_attempts: int,
    provider_name: str,
) -> PhotoProcessingJob:
    from app.core.config import get_settings

    settings = get_settings()
    return create_next_job(
        db,
        photo_id,
        job_type=PHOTO_JOB_TYPE_CAPTION_REGENERATE,
        max_attempts=max_attempts,
        provider_name=provider_name,
        model=settings.deepseek_model or "",
        prompt_version="caption_regen.v1",
    )


def create_template_regenerate_job(
    db: Session,
    photo_id: str,
    *,
    max_attempts: int,
    provider_name: str,
) -> PhotoProcessingJob:
    from app.core.config import get_settings

    settings = get_settings()
    return create_next_job(
        db,
        photo_id,
        job_type=PHOTO_JOB_TYPE_TEMPLATE_REGENERATE,
        max_attempts=max_attempts,
        provider_name=provider_name,
        model=settings.deepseek_model or "",
        prompt_version="template_regen.v1",
    )


def create_css_regenerate_job(
    db: Session,
    photo_id: str,
    *,
    max_attempts: int,
    provider_name: str,
) -> PhotoProcessingJob:
    from app.core.config import get_settings

    settings = get_settings()
    return create_next_job(
        db,
        photo_id,
        job_type=PHOTO_JOB_TYPE_CSS_REGENERATE,
        max_attempts=max_attempts,
        provider_name=provider_name,
        model=settings.deepseek_model or "",
        prompt_version="css_regen.v1",
    )


def create_fallback_regenerate_job(
    db: Session,
    photo_id: str,
    *,
    max_attempts: int,
) -> PhotoProcessingJob:
    return create_next_job(
        db,
        photo_id,
        job_type=PHOTO_JOB_TYPE_FALLBACK_REGENERATE,
        max_attempts=max_attempts,
    )


def process_vision_analyze_job(
    db: Session,
    job: PhotoProcessingJob,
    photo: Photo,
    storage: ObjectStorage,
    *,
    _provider: object = None,
) -> bool:
    """Run vision analysis via Ollama for a ready photo."""
    if not photo.object_key_preview:
        from app.services.ai.ollama_provider import VisionAnalysisResult
        _mark_ai_job_failed(db, job, photo, "No preview available for vision analysis")
        return True

    try:
        if _provider is not None and hasattr(_provider, "analyze"):
            result = _provider.analyze(storage.download_bytes(photo.object_key_preview))
        else:
            from app.services.ai.ollama_provider import analyze_preview
            result = analyze_preview(storage, photo.object_key_preview, enabled=True)
    except Exception as exc:
        _mark_ai_job_failed(db, job, photo, str(exc))
        return True

    if result is None:
        _mark_ai_job_failed(db, job, photo, "Vision analysis returned no result")
        return True

    _mark_vision_job_succeeded(db, job, photo, result)
    return True


def _mark_vision_job_succeeded(
    db: Session,
    job: PhotoProcessingJob,
    photo: Photo,
    result: object,
) -> None:
    """Write ai_analysis_json and mark vision job succeeded. Photo status unchanged."""
    from app.services.ai.ollama_provider import VisionAnalysisResult

    now = utc_now()
    if isinstance(result, VisionAnalysisResult):
        from dataclasses import asdict
        photo.ai_analysis_json = asdict(result)
        suggested_category = result.suggested_category if result.suggested_category in AI_CATEGORY_SLUGS else None
        photo.ai_category_suggestion = suggested_category
        if (
            suggested_category
            and photo.ai_category_enabled
            and photo.category_source in {"fallback", "ai", "none"}
            and not photo.category_source.startswith("admin")
        ):
            photo.category = suggested_category
            photo.category_source = "ai"
    else:
        photo.ai_analysis_json = result  # type: ignore[assignment]
    photo.updated_at = now
    job.status = PHOTO_JOB_STATUS_SUCCEEDED
    job.error_message = None
    job.finished_at = now
    job.updated_at = now
    db.add(photo)
    db.add(job)
    db.commit()


def _mark_ai_job_failed(
    db: Session,
    job: PhotoProcessingJob,
    photo: Photo | None,
    error_message: str,
) -> None:
    """Record AI job failure. Photo status UNCHANGED."""
    now = utc_now()
    if job.attempts >= job.max_attempts:
        job.status = PHOTO_JOB_STATUS_FAILED
        job.finished_at = now
    else:
        job.status = PHOTO_JOB_STATUS_PENDING
        job.finished_at = None
    job.error_message = error_message[:2000]
    job.updated_at = now
    if photo is not None:
        photo.updated_at = now
        db.add(photo)
    db.add(job)
    db.commit()


def _get_vision_result(photo: Photo):
    from app.services.ai.ollama_provider import VisionAnalysisResult

    if not photo.ai_analysis_json:
        return None
    try:
        return VisionAnalysisResult(**photo.ai_analysis_json)
    except Exception:
        return None


def _get_prev_errors(job: PhotoProcessingJob) -> list[str] | None:
    if job.error_message and job.attempts > 1:
        return [job.error_message]
    return None


def _location_summary(photo: Photo) -> str | None:
    location_parts = [
        photo.location_name,
        photo.location_city,
        photo.location_region,
        photo.location_country,
    ]
    return ", ".join(p for p in location_parts if p) or None


def _extract_caption_from_design(design_json: dict) -> str | None:
    for layer in design_json.get("layers", []):
        if (
            isinstance(layer, dict)
            and layer.get("type") == "text"
            and layer.get("role") == "caption"
        ):
            content = layer.get("content")
            if isinstance(content, str) and content.strip():
                return content.strip()[:200]
    return None


def _sync_caption_layers(design_json: dict, caption: str | None) -> dict:
    layers = design_json.get("layers")
    if not isinstance(layers, list):
        return design_json
    synced_layers: list[object] = []
    for layer in layers:
        if (
            isinstance(layer, dict)
            and layer.get("type") == "text"
            and layer.get("role") == "caption"
        ):
            if caption:
                updated = deepcopy(layer)
                updated["content"] = caption
                synced_layers.append(updated)
            continue
        synced_layers.append(layer)
    design_json["layers"] = synced_layers
    return design_json


def _apply_caption_outputs(photo: Photo, design_json: dict) -> dict:
    generated_caption = _extract_caption_from_design(design_json)
    if photo.user_message:
        photo.ai_caption = None
        if photo.caption_source != "admin":
            final_caption, caption_source = compute_final_caption(photo)
            photo.final_caption = final_caption
            photo.caption_source = caption_source
        return _sync_caption_layers(design_json, photo.final_caption)

    if photo.ai_caption_enabled:
        if not generated_caption:
            raise ValueError("AI caption enabled requires a non-empty caption layer")
        photo.ai_caption = generated_caption
        if photo.caption_source != "admin":
            final_caption, caption_source = compute_final_caption(photo)
            photo.final_caption = final_caption
            photo.caption_source = caption_source
        return _sync_caption_layers(design_json, photo.final_caption)

    photo.ai_caption = None
    if photo.caption_source != "admin":
        final_caption, caption_source = compute_final_caption(photo)
        photo.final_caption = final_caption
        photo.caption_source = caption_source
    return _sync_caption_layers(design_json, photo.final_caption)


def _publish_new_active_design(
    db: Session,
    photo: Photo,
    job: PhotoProcessingJob,
    design_json: dict,
    *,
    source: str,
) -> None:
    from app.services.slide_designs import SLIDE_DESIGN_STATUS_ACTIVE

    active_design = get_latest_active_slide_design(db, photo.id)
    now = utc_now()
    if active_design is not None and active_design.status == SLIDE_DESIGN_STATUS_ACTIVE:
        active_design.status = "draft"
        active_design.updated_at = now
        db.add(active_design)

    create_slide_design(
        db,
        photo.id,
        SlideDesignCreate(
            version=get_latest_slide_design_version(db, photo.id) + 1,
            design_json=design_json,
            source=source,
            status="active",
            validation_errors=None,
        ),
    )

    photo.updated_at = now
    job.status = PHOTO_JOB_STATUS_SUCCEEDED
    job.error_message = None
    job.finished_at = now
    job.updated_at = now
    db.add(photo)
    db.add(job)
    db.commit()


def _score_design_or_raise(design: dict[str, object]) -> None:
    from app.services.ai.quality_scorer import score_design_quality

    template_id = design.get("templateId")
    template_def = get_template_definition(template_id) if isinstance(template_id, str) else None
    max_extra_layers = 4
    if isinstance(template_def, dict) and isinstance(template_def.get("maxExtraLayers"), int):
        max_extra_layers = int(template_def["maxExtraLayers"])

    report = score_design_quality(design, max_extra_layers=max_extra_layers)
    if not report.passed:
        failures = "; ".join(report.failures or [])
        raise ValueError(f"quality score {report.total_score}/5 below threshold: {failures or 'quality rules not met'}")


def _require_non_manual_active_design(db: Session, job: PhotoProcessingJob, photo: Photo):
    active_design = get_latest_active_slide_design(db, photo.id)
    if active_design is None:
        _mark_ai_job_failed(db, job, photo, "No active slide design available")
        return None
    if active_design.source == "manual":
        _mark_ai_job_failed(db, job, photo, "Active design is manual — AI cannot overwrite")
        return None
    return active_design


def _call_design_provider(job: PhotoProcessingJob, prompt: str, *, _provider: object = None) -> dict | None:
    if _provider is not None and hasattr(_provider, "generate"):
        return _provider.generate(prompt)

    from app.services.ai.deepseek_provider import generate_slide_design_from_context

    return generate_slide_design_from_context(prompt)


def process_slide_design_generate_job(
    db: Session,
    job: PhotoProcessingJob,
    photo: Photo,
    *,
    _provider: object = None,
) -> bool:
    """Generate a slide design via DeepSeek, validate it, and atomically replace active."""
    from app.schemas.slide_design_validator import validate_slide_design_data
    from app.services.ai.slide_design_prompt import build_slide_design_prompt

    active_design = _require_non_manual_active_design(db, job, photo)
    if active_design is None:
        return True

    prompt = build_slide_design_prompt(
        photo_id=photo.id,
        photo_category=photo.category,
        user_message=photo.user_message,
        ai_caption_enabled=photo.ai_caption_enabled,
        taken_at_str=photo.taken_at.isoformat() if photo.taken_at else "",
        location_summary=_location_summary(photo),
        vision_result=_get_vision_result(photo),
        prev_errors=_get_prev_errors(job),
    )

    try:
        design_json = _call_design_provider(job, prompt, _provider=_provider)
    except Exception as exc:
        _mark_ai_job_failed(db, job, photo, str(exc))
        return True

    if design_json is None:
        _mark_ai_job_failed(db, job, photo, "DeepSeek returned no valid response")
        return True

    try:
        validated = validate_slide_design_data(design_json, photo_id=photo.id)
        validated = _apply_caption_outputs(photo, validated)
        _score_design_or_raise(validated)
    except ValueError as exc:
        _mark_ai_job_failed(db, job, photo, str(exc))
        return True

    _publish_new_active_design(db, photo, job, validated, source="ai")
    return True


def process_caption_regenerate_job(
    db: Session,
    job: PhotoProcessingJob,
    photo: Photo,
    *,
    _provider: object = None,
) -> bool:
    from app.services.ai.slide_design_prompt import build_caption_regeneration_prompt
    from app.schemas.slide_design_validator import validate_slide_design_data

    active_design = _require_non_manual_active_design(db, job, photo)
    if active_design is None:
        return True

    prompt = build_caption_regeneration_prompt(
        photo_id=photo.id,
        photo_category=photo.category,
        user_message=photo.user_message,
        taken_at_str=photo.taken_at.isoformat() if photo.taken_at else "",
        location_summary=_location_summary(photo),
        vision_result=_get_vision_result(photo),
        active_design=active_design.design_json,
        prev_errors=_get_prev_errors(job),
    )
    try:
        response = _call_design_provider(job, prompt, _provider=_provider)
    except Exception as exc:
        _mark_ai_job_failed(db, job, photo, str(exc))
        return True
    if not isinstance(response, dict):
        _mark_ai_job_failed(db, job, photo, "Caption regeneration returned no valid JSON")
        return True

    caption = response.get("caption")
    if caption is not None and not isinstance(caption, str):
        _mark_ai_job_failed(db, job, photo, "Caption regeneration must return string|null")
        return True
    if isinstance(caption, str) and len(caption) > 200:
        caption = caption[:200]

    photo.ai_caption = caption
    if photo.caption_source != "admin":
        final_caption, caption_source = compute_final_caption(photo)
        photo.final_caption = final_caption
        photo.caption_source = caption_source

    design_json = deepcopy(active_design.design_json)
    display_caption = photo.final_caption
    for layer in design_json.get("layers", []):
        if isinstance(layer, dict) and layer.get("type") == "text" and layer.get("role") == "caption":
            if display_caption:
                layer["content"] = display_caption

    try:
        validated = validate_slide_design_data(design_json, photo_id=photo.id)
    except ValueError as exc:
        _mark_ai_job_failed(db, job, photo, str(exc))
        return True

    _publish_new_active_design(db, photo, job, validated, source="ai")
    return True


def process_template_regenerate_job(
    db: Session,
    job: PhotoProcessingJob,
    photo: Photo,
    *,
    _provider: object = None,
) -> bool:
    from app.services.ai.slide_design_prompt import build_template_regeneration_prompt
    from app.schemas.slide_design_validator import validate_slide_design_data

    active_design = _require_non_manual_active_design(db, job, photo)
    if active_design is None:
        return True

    prompt = build_template_regeneration_prompt(
        photo_id=photo.id,
        photo_category=photo.category,
        user_message=photo.user_message,
        ai_caption_enabled=photo.ai_caption_enabled,
        taken_at_str=photo.taken_at.isoformat() if photo.taken_at else "",
        location_summary=_location_summary(photo),
        vision_result=_get_vision_result(photo),
        active_design=active_design.design_json,
        prev_errors=_get_prev_errors(job),
    )
    try:
        response = _call_design_provider(job, prompt, _provider=_provider)
    except Exception as exc:
        _mark_ai_job_failed(db, job, photo, str(exc))
        return True
    if not isinstance(response, dict):
        _mark_ai_job_failed(db, job, photo, "Template regeneration returned no valid JSON")
        return True

    template_id = response.get("templateId")
    if not isinstance(template_id, str):
        _mark_ai_job_failed(db, job, photo, "Template regeneration must return templateId")
        return True

    design_json = deepcopy(active_design.design_json)
    design_json["templateId"] = template_id
    current_params = design_json.get("templateParams")
    merged_params = deepcopy(current_params) if isinstance(current_params, dict) else {}
    if isinstance(response.get("templateParams"), dict):
        merged_params.update(response["templateParams"])
    design_json["templateParams"] = merged_params

    try:
        validated = validate_slide_design_data(design_json, photo_id=photo.id)
        _score_design_or_raise(validated)
    except ValueError as exc:
        _mark_ai_job_failed(db, job, photo, str(exc))
        return True

    _publish_new_active_design(db, photo, job, validated, source="ai")
    return True


def process_css_regenerate_job(
    db: Session,
    job: PhotoProcessingJob,
    photo: Photo,
    *,
    _provider: object = None,
) -> bool:
    from app.services.ai.slide_design_prompt import build_css_regeneration_prompt
    from app.schemas.slide_design_validator import validate_slide_design_data

    active_design = _require_non_manual_active_design(db, job, photo)
    if active_design is None:
        return True

    prompt = build_css_regeneration_prompt(
        photo_id=photo.id,
        photo_category=photo.category,
        user_message=photo.user_message,
        ai_caption_enabled=photo.ai_caption_enabled,
        taken_at_str=photo.taken_at.isoformat() if photo.taken_at else "",
        location_summary=_location_summary(photo),
        vision_result=_get_vision_result(photo),
        active_design=active_design.design_json,
        prev_errors=_get_prev_errors(job),
    )
    try:
        response = _call_design_provider(job, prompt, _provider=_provider)
    except Exception as exc:
        _mark_ai_job_failed(db, job, photo, str(exc))
        return True
    if not isinstance(response, dict) or not isinstance(response.get("styleTokens"), dict):
        _mark_ai_job_failed(db, job, photo, "CSS regeneration must return styleTokens object")
        return True

    design_json = deepcopy(active_design.design_json)
    design_json["styleTokens"] = response["styleTokens"]
    if isinstance(response.get("scopedCss"), str):
        design_json["scopedCss"] = response["scopedCss"]

    try:
        validated = validate_slide_design_data(design_json, photo_id=photo.id)
        _score_design_or_raise(validated)
    except ValueError as exc:
        _mark_ai_job_failed(db, job, photo, str(exc))
        return True

    _publish_new_active_design(db, photo, job, validated, source="ai")
    return True


def process_fallback_regenerate_job(
    db: Session,
    job: PhotoProcessingJob,
    photo: Photo,
) -> bool:
    metadata = ExtractedMetadata(
        width=photo.width,
        height=photo.height,
        taken_at=photo.taken_at,
        gps_lat=photo.gps_lat,
        gps_lng=photo.gps_lng,
        camera_make=photo.camera_make,
        camera_model=photo.camera_model,
        exif_json=photo.exif_json,
    )
    design_json = build_fallback_slide_design(photo, metadata)
    _publish_new_active_design(db, photo, job, design_json, source="fallback")
    return True


def process_reverse_geocode_job(
    db: Session,
    job: PhotoProcessingJob,
    photo: Photo,
    geocoding: GeocodingService,
) -> bool:
    """Attempt reverse geocoding for a photo with GPS coordinates."""

    if not geocoding.enabled:
        mark_geocode_job_failed(db, job, photo, "Geocoding is disabled")
        return True
    if photo.gps_lat is None or photo.gps_lng is None:
        mark_geocode_job_failed(db, job, photo, "No GPS coordinates available")
        return True
    try:
        result = geocoding.reverse_geocode(photo.gps_lat, photo.gps_lng)
    except Exception as exc:
        mark_geocode_job_failed(db, job, photo, str(exc))
        return True
    if result is None:
        mark_geocode_job_failed(db, job, photo, "No geocoding results returned")
    else:
        mark_geocode_job_succeeded(db, job, photo, result, geocoding.provider_name)
    return True


def process_next_photo_job(
    db: Session,
    storage: ObjectStorage,
    *,
    thumbnail_size_px: int = 512,
    preview_max_size_px: int = 2048,
    geocoding: GeocodingService | None = None,
    geocoding_max_attempts: int = 2,
    ai_enabled: bool = False,
    ai_max_attempts: int = 2,
) -> bool:
    """Process one pending photo job if one is available."""

    job = claim_next_pending_job(db)
    if job is None:
        return False

    photo = db.get(Photo, job.photo_id)

    # ── Job-type dispatch ────────────────────────────────────────
    if job.job_type == PHOTO_JOB_TYPE_REVERSE_GEOCODE:
        if photo is None:
            mark_geocode_job_failed(db, job, None, "Photo not found")
            return True
        if geocoding is None:
            mark_geocode_job_failed(db, job, photo, "Geocoding service not available")
            return True
        return process_reverse_geocode_job(db, job, photo, geocoding)

    if job.job_type == PHOTO_JOB_TYPE_VISION_ANALYZE:
        if photo is None:
            _mark_ai_job_failed(db, job, None, "Photo not found")
            return True
        result = process_vision_analyze_job(db, job, photo, storage)
        # Enqueue slide_design_generate after vision completes
        if ai_enabled:
            from app.core.config import get_settings
            settings = get_settings()
            create_slide_design_generate_job(
                db,
                photo.id,
                max_attempts=ai_max_attempts,
                provider_name="deepseek",
            )
        return result

    if job.job_type == PHOTO_JOB_TYPE_SLIDE_DESIGN_GENERATE:
        if photo is None:
            _mark_ai_job_failed(db, job, None, "Photo not found")
            return True
        return process_slide_design_generate_job(db, job, photo)

    if job.job_type == PHOTO_JOB_TYPE_CAPTION_REGENERATE:
        if photo is None:
            _mark_ai_job_failed(db, job, None, "Photo not found")
            return True
        return process_caption_regenerate_job(db, job, photo)

    if job.job_type == PHOTO_JOB_TYPE_TEMPLATE_REGENERATE:
        if photo is None:
            _mark_ai_job_failed(db, job, None, "Photo not found")
            return True
        return process_template_regenerate_job(db, job, photo)

    if job.job_type == PHOTO_JOB_TYPE_CSS_REGENERATE:
        if photo is None:
            _mark_ai_job_failed(db, job, None, "Photo not found")
            return True
        return process_css_regenerate_job(db, job, photo)

    if job.job_type == PHOTO_JOB_TYPE_FALLBACK_REGENERATE:
        if photo is None:
            _mark_ai_job_failed(db, job, None, "Photo not found")
            return True
        return process_fallback_regenerate_job(db, job, photo)

    try:
        if photo is None:
            raise RuntimeError(f"Photo does not exist: {job.photo_id}")
        original_bytes = storage.download_bytes(photo.object_key_original)
        suffix = Path(photo.object_key_original).suffix or ".jpg"
        metadata = extract_metadata(original_bytes, suffix, photo.uploaded_at)

        photo.status = PHOTO_STATUS_EXIF_PARSED
        photo.updated_at = utc_now()
        db.add(photo)
        db.commit()

        thumbnail_bytes = generate_thumbnail(original_bytes, max_size=thumbnail_size_px)
        preview_bytes = generate_preview(original_bytes, max_size=preview_max_size_px)
        storage.upload_bytes(photo.object_key_thumbnail, thumbnail_bytes, "image/webp")
        if photo.object_key_preview is not None:
            storage.upload_bytes(photo.object_key_preview, preview_bytes, "image/webp")

        photo.status = PHOTO_STATUS_PREVIEW_GENERATED
        photo.updated_at = utc_now()
        db.add(photo)
        db.commit()

        design_json = build_fallback_slide_design(photo, metadata)
        create_slide_design(
            db,
            photo.id,
            SlideDesignCreate(
                version=get_latest_slide_design_version(db, photo.id) + 1,
                design_json=design_json,
                source="fallback",
                status="active",
                validation_errors=None,
            ),
        )

        photo.status = PHOTO_STATUS_DESIGN_GENERATED
        photo.updated_at = utc_now()
        db.add(photo)
        db.commit()
    except Exception as exc:
        mark_job_failed(db, job, photo, str(exc))
        return True

    mark_job_succeeded(db, job, photo, metadata)

    # ── Enqueue reverse geocoding if GPS exists ────────────────
    if (
        geocoding is not None
        and geocoding.enabled
        and metadata.gps_lat is not None
        and metadata.gps_lng is not None
    ):
        create_reverse_geocode_job(
            db,
            photo.id,
            max_attempts=geocoding_max_attempts,
            provider_name=geocoding.provider_name,
        )

    # ── Enqueue vision_analyze if AI enabled ──────────────────
    if ai_enabled:
        create_vision_analyze_job(
            db,
            photo.id,
            max_attempts=ai_max_attempts,
        )

    return True
