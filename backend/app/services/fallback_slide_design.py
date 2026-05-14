"""Deterministic fallback slide design generator."""

from datetime import datetime

from app.models import Photo
from app.services.exif import ExtractedMetadata

FALLBACK_TEMPLATES = {
    "cinematic_fullscreen",
    "warm_memory",
    "minimal_white",
    "poetic_landscape",
    "magazine_left",
    "gallery_center",
    "dark_exhibition",
    "pet_portrait",
}


def _template_for_category(category: str, photo_id: str = "") -> str:
    """Select a deterministic template based on category and photo ID hash.

    Uses photo ID hash for variety within a category while keeping
    the result deterministic (same photo always gets same template).
    """
    preferred: dict[str, list[str]] = {
        "photography": ["gallery_center", "cinematic_fullscreen", "dark_exhibition", "poetic_landscape"],
        "travel": ["poetic_landscape", "cinematic_fullscreen", "dark_exhibition"],
        "life": ["warm_memory", "magazine_left"],
        "pet": ["pet_portrait", "minimal_white", "warm_memory"],
    }

    candidates = preferred.get(category, ["warm_memory", "cinematic_fullscreen"])
    # Deterministic selection via photo ID hash for variety
    idx = hash(photo_id) % len(candidates)
    return candidates[idx]


_TEMPLATE_STYLE_TOKENS: dict[str, dict[str, str]] = {
    "cinematic_fullscreen": {
        "--kf-background-color": "#111111",
        "--kf-text-color": "#f8fafc",
        "--kf-accent-color": "#d8b26e",
    },
    "warm_memory": {
        "--kf-background-color": "#f7f5ef",
        "--kf-text-color": "#171717",
        "--kf-accent-color": "#8a9a5b",
    },
    "minimal_white": {
        "--kf-background-color": "#f7f5ef",
        "--kf-text-color": "#171717",
        "--kf-accent-color": "#d8b26e",
    },
    "poetic_landscape": {
        "--kf-background-color": "#0d1b2a",
        "--kf-text-color": "#e0e1dd",
        "--kf-accent-color": "#778da9",
    },
    "magazine_left": {
        "--kf-background-color": "#faf9f6",
        "--kf-text-color": "#2c2c2c",
        "--kf-accent-color": "#b5838d",
    },
    "gallery_center": {
        "--kf-background-color": "#f5f5f0",
        "--kf-text-color": "#1a1a1a",
        "--kf-accent-color": "#6b6b6b",
    },
    "dark_exhibition": {
        "--kf-background-color": "#0a0a0a",
        "--kf-text-color": "#d4d4d4",
        "--kf-accent-color": "#c9a96e",
    },
    "pet_portrait": {
        "--kf-background-color": "#fef9ef",
        "--kf-text-color": "#3d2c2c",
        "--kf-accent-color": "#d4a574",
    },
}


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

    template_id = _template_for_category(photo.category, photo.id)
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
    tokens = _TEMPLATE_STYLE_TOKENS.get(template_id, _TEMPLATE_STYLE_TOKENS["warm_memory"])
    return {
        "photoId": photo.id,
        "templateId": template_id,
        "templateParams": {
            "imageRect": image_rect,
            "safeArea": {"x": 0.05, "y": 0.05, "width": 0.9, "height": 0.9},
            "orientation": "portrait" if metadata.width and metadata.height and metadata.height > metadata.width else "landscape",
        },
        "layers": layers,
        "styleTokens": dict(tokens),
        "renderPolicy": {"mode": "fallback", "allowHtml": False, "allowJavaScript": False},
    }
