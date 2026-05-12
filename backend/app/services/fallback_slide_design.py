"""Deterministic fallback slide design generator."""

from datetime import datetime

from app.models import Photo
from app.services.exif import ExtractedMetadata

FALLBACK_TEMPLATES = {
    "cinematic_fullscreen",
    "warm_memory",
    "minimal_white",
}


def _template_for_category(category: str) -> str:
    if category in {"travel", "photography"}:
        return "cinematic_fullscreen"
    if category == "pet":
        return "minimal_white"
    return "warm_memory"


def _image_rect(width: int | None, height: int | None) -> dict[str, float]:
    if width and height and height > width:
        return {"x": 0.18, "y": 0.06, "width": 0.64, "height": 0.82}
    return {"x": 0.06, "y": 0.08, "width": 0.88, "height": 0.74}


def _caption_rect(width: int | None, height: int | None) -> dict[str, float]:
    if width and height and height > width:
        return {"x": 0.18, "y": 0.82, "width": 0.64, "height": 0.1}
    return {"x": 0.08, "y": 0.78, "width": 0.72, "height": 0.1}


def _timeline_label(value: datetime) -> str:
    return value.date().isoformat()


def build_fallback_slide_design(photo: Photo, metadata: ExtractedMetadata) -> dict:
    """Build schema-shaped fallback design data for one processed photo."""

    template_id = _template_for_category(photo.category)
    image_rect = _image_rect(metadata.width, metadata.height)
    layers: list[dict] = [
        {
            "id": "background",
            "type": "shape",
            "role": "background",
            "zIndex": 0,
            "rect": {"x": 0, "y": 0, "width": 1, "height": 1},
            "style": {"fill": "var(--kf-background-color)"},
        },
        {
            "id": "photo",
            "type": "image",
            "role": "main",
            "source": "preview",
            "zIndex": 10,
            "rect": image_rect,
            "fit": "contain",
        },
    ]
    if photo.user_message:
        layers.append(
            {
                "id": "caption",
                "type": "text",
                "role": "caption",
                "zIndex": 20,
                "rect": _caption_rect(metadata.width, metadata.height),
                "content": photo.user_message,
                "style": {"color": "var(--kf-text-color)", "fontSize": "clamp(16px, 2vw, 28px)"},
            }
        )
    layers.append(
        {
            "id": "timeline",
            "type": "timeline",
            "role": "taken_at",
            "zIndex": 30,
            "rect": {"x": 0.08, "y": 0.91, "width": 0.84, "height": 0.05},
            "label": _timeline_label(metadata.taken_at),
        }
    )
    return {
        "photoId": photo.id,
        "templateId": template_id,
        "templateParams": {
            "imageRect": image_rect,
            "safeArea": {"x": 0.05, "y": 0.05, "width": 0.9, "height": 0.9},
            "orientation": "portrait" if metadata.width and metadata.height and metadata.height > metadata.width else "landscape",
        },
        "layers": layers,
        "styleTokens": {
            "--kf-background-color": "#111111" if template_id == "cinematic_fullscreen" else "#f7f5ef",
            "--kf-text-color": "#f8fafc" if template_id == "cinematic_fullscreen" else "#171717",
            "--kf-accent-color": "#8a9a5b" if template_id == "warm_memory" else "#d8b26e",
        },
        "renderPolicy": {"mode": "fallback", "allowHtml": False, "allowJavaScript": False},
    }
