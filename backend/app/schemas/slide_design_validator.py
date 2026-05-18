"""Semantic validation for KinFrame slide design JSON."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.schemas.slide_design_assets import (
    get_layer_types,
    get_template_ids,
    load_design_presets,
)
from app.services.scoped_css import sanitize_scoped_css

ALLOWED_TEMPLATE_IDS = set(get_template_ids())
ALLOWED_LAYER_TYPES = set(get_layer_types())
REQUIRED_DESIGN_KEYS = {"photoId", "templateId", "templateParams", "layers", "styleTokens", "renderPolicy"}
RECT_KEYS = {"x", "y", "width", "height"}

BLOCKED_CSS_VALUE_TOKENS = [
    "position:", "display:", "flex", "grid", "transform:", "z-index:",
    "overflow:", "visibility:", "pointer-events:",
]
PRESET_CATEGORIES = ("shadows", "masks", "lightOrbs", "timelines", "fonts")
IMAGE_SOURCE_ALIASES = {
    "photo": "preview",
    "image": "preview",
    "main": "preview",
    "cover": "preview",
    "hero": "preview",
    "preview_image": "preview",
    "photo_preview": "preview",
    "thumb": "thumbnail",
    "thumbnail_image": "thumbnail",
    "full": "original",
    "fullsize": "original",
    "source": "original",
}


def _assert_unit_interval(value: Any, label: str) -> None:
    if not isinstance(value, int | float) or not 0 <= value <= 1:
        raise ValueError(f"{label} must be a number between 0 and 1")


def _expand_preset_ref(layer: dict[str, Any]) -> dict[str, Any] | None:
    preset_ref = layer.get("presetRef")
    if not isinstance(preset_ref, str):
        return layer

    presets = load_design_presets()
    for category in PRESET_CATEGORIES:
        bucket = presets.get(category)
        if not isinstance(bucket, dict) or preset_ref not in bucket:
            continue
        preset = bucket[preset_ref]
        if not isinstance(preset, dict):
            return layer

        source = preset.get("layer") if isinstance(preset.get("layer"), dict) else preset
        expanded = deepcopy(layer)
        expanded.pop("presetRef", None)
        if isinstance(source, dict):
            for key, value in source.items():
                if key == "name":
                    continue
                expanded.setdefault(key, value)
        return expanded

    return None


def _sanitize_style_tokens(tokens: dict[str, Any]) -> dict[str, str]:
    """Remove non-whitelisted or dangerous CSS variable tokens."""
    out: dict[str, str] = {}
    for key, val in tokens.items():
        if not isinstance(key, str) or not key.startswith("--kf-"):
            continue
        if not isinstance(val, str):
            continue
        lower = val.lower()
        if any(bad in lower for bad in ("javascript:", "expression(", "@import", "url(")):
            continue
        if any(token in lower for token in BLOCKED_CSS_VALUE_TOKENS):
            continue
        out[key] = val
    return out


def _normalize_image_source(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    if normalized in ("preview", "thumbnail", "original"):
        return normalized
    return IMAGE_SOURCE_ALIASES.get(normalized)


def _normalize_font_size(value: Any) -> str | None:
    if isinstance(value, int | float):
        if 0 < value <= 1:
            return f"{round(float(value) * 100, 3)}vw"
        return f"{int(value)}px" if float(value).is_integer() else f"{value}px"
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _expand_layer_props(layer: dict[str, Any]) -> dict[str, Any]:
    props = layer.get("props")
    if not isinstance(props, dict):
        return layer

    expanded = deepcopy(layer)
    expanded.pop("props", None)

    for key in ("role", "source", "content", "fit", "presetRef", "label", "timeText", "locationText"):
        if key not in expanded and key in props:
            expanded[key] = props[key]

    style = deepcopy(expanded.get("style")) if isinstance(expanded.get("style"), dict) else {}
    fill = deepcopy(expanded.get("fill")) if isinstance(expanded.get("fill"), dict) else None

    if "backgroundColor" in props and "color" not in style:
        style["color"] = props["backgroundColor"]
    if "color" in props and "color" not in style:
        style["color"] = props["color"]
    if "textAlign" in props and "textAlign" not in style:
        style["textAlign"] = props["textAlign"]
    if "fontFamily" in props and "fontFamily" not in style:
        style["fontFamily"] = props["fontFamily"]
    if "fontWeight" in props and "fontWeight" not in style:
        style["fontWeight"] = props["fontWeight"]
    if "letterSpacing" in props and "letterSpacing" not in style:
        style["letterSpacing"] = props["letterSpacing"]
    if "lineHeight" in props and "lineHeight" not in style:
        style["lineHeight"] = props["lineHeight"]

    font_size = _normalize_font_size(props.get("fontSize"))
    if font_size and "fontSize" not in style:
        style["fontSize"] = font_size

    if props.get("shapeType") == "line" and "fill" not in style and isinstance(props.get("borderColor"), str):
        style["fill"] = props["borderColor"]
    elif "fill" in props and "fill" not in style and isinstance(props.get("fill"), str):
        style["fill"] = props["fill"]

    if isinstance(props.get("opacity"), int | float) and "opacity" not in style:
        style["opacity"] = props["opacity"]
    if isinstance(props.get("borderRadius"), str) and "borderRadius" not in style:
        style["borderRadius"] = props["borderRadius"]

    if style:
        expanded["style"] = style
    if fill is not None:
        expanded["fill"] = fill
    return expanded


def _sanitize_style_payload(
    raw_tokens: dict[str, Any],
    *,
    top_level_scoped_css: str | None = None,
) -> tuple[dict[str, str], str | None]:
    css_variables_source: dict[str, Any]
    if isinstance(raw_tokens.get("cssVariables"), dict):
        css_variables_source = raw_tokens["cssVariables"]
    else:
        css_variables_source = raw_tokens

    scoped_css = raw_tokens.get("scopedCss") if isinstance(raw_tokens.get("scopedCss"), str) else top_level_scoped_css
    tokens = _sanitize_style_tokens(css_variables_source)
    safe_css: str | None = None
    if scoped_css:
        result = sanitize_scoped_css(scoped_css)
        if result.safe_css.strip():
            safe_css = result.safe_css
    return tokens, safe_css


def validate_slide_design_data(value: dict[str, Any], *, photo_id: str | None = None) -> dict[str, Any]:
    """Validate the subset of slide design JSON supported by v0.2."""
    value = deepcopy(value)

    missing = REQUIRED_DESIGN_KEYS - set(value)
    if missing:
        raise ValueError(f"slide design is missing required keys: {sorted(missing)}")
    if value["templateId"] not in ALLOWED_TEMPLATE_IDS:
        raise ValueError("templateId is not supported")
    if not isinstance(value["templateParams"], dict):
        raise ValueError("templateParams must be an object")

    # photoId cross-check
    if photo_id is not None and value.get("photoId") != photo_id:
        raise ValueError(f"photoId mismatch: expected {photo_id}")

    # ── styleTokens sanitization ─────────────────────────────────
    tokens = value["styleTokens"]
    if not isinstance(tokens, dict):
        raise ValueError("styleTokens must be an object")
    sanitized_tokens, safe_css = _sanitize_style_payload(
        tokens,
        top_level_scoped_css=value.get("scopedCss") if isinstance(value.get("scopedCss"), str) else None,
    )
    if safe_css:
        sanitized_tokens["scopedCss"] = safe_css
    value["styleTokens"] = sanitized_tokens
    value.pop("scopedCss", None)

    # ── renderPolicy ─────────────────────────────────────────────
    render_policy = value["renderPolicy"]
    if not isinstance(render_policy, dict):
        raise ValueError("renderPolicy must be an object")
    if render_policy.get("allowHtml") is not False or render_policy.get("allowJavaScript") is not False:
        raise ValueError("fallback slide designs cannot allow HTML or JavaScript")

    # ── layers ───────────────────────────────────────────────────
    layers = value["layers"]
    if not isinstance(layers, list) or not layers:
        raise ValueError("layers must be a non-empty list")

    has_image_layer = False
    validated_layers: list[dict[str, Any]] = []
    for index, raw_layer in enumerate(layers):
        layer = raw_layer
        if not isinstance(layer, dict):
            raise ValueError(f"layer {index} must be an object")
        expanded = _expand_preset_ref(layer)
        if expanded is None:
            continue
        layer = _expand_layer_props(expanded)
        layer_type = layer.get("type")
        if layer_type not in ALLOWED_LAYER_TYPES:
            raise ValueError(f"layer {index} has unsupported type: {layer_type}")

        if layer_type == "image":
            has_image_layer = True
            source = _normalize_image_source(layer.get("source"))
            if source not in ("preview", "thumbnail", "original"):
                raise ValueError(f"layer {index} image source must be preview/thumbnail/original")
            layer["source"] = source

        z_index = layer.get("zIndex")
        if not isinstance(z_index, int) or not 0 <= z_index <= 100:
            raise ValueError(f"layer {index} zIndex must be an integer between 0 and 100")
        if "html" in layer or "script" in layer:
            raise ValueError(f"layer {index} cannot include executable content")

        if "rect" in layer:
            rect = layer["rect"]
            if not isinstance(rect, dict) or set(rect) != RECT_KEYS:
                raise ValueError(f"layer {index} rect must contain x, y, width, height")
            for key in RECT_KEYS:
                _assert_unit_interval(rect[key], f"layer {index} rect.{key}")
            if rect["width"] <= 0 or rect["height"] <= 0:
                raise ValueError(f"layer {index} rect width/height must be > 0")

        if layer_type == "text" and isinstance(layer.get("content"), str):
            content = layer["content"]
            if len(content) > 200:
                layer["content"] = content[:200]
        validated_layers.append(layer)

    if not has_image_layer:
        raise ValueError("layers must include at least one image layer")
    value["layers"] = validated_layers

    return value
