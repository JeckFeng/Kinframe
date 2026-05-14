"""Semantic validation for KinFrame v0.2 slide design JSON."""

from typing import Any

ALLOWED_TEMPLATE_IDS = {
    "cinematic_fullscreen",
    "warm_memory",
    "minimal_white",
    "poetic_landscape",
    "magazine_left",
    "gallery_center",
    "dark_exhibition",
    "pet_portrait",
}
ALLOWED_LAYER_TYPES = {"shape", "image", "text", "timeline", "background", "mask", "texture", "vignette"}
REQUIRED_DESIGN_KEYS = {"photoId", "templateId", "templateParams", "layers", "styleTokens", "renderPolicy"}
RECT_KEYS = {"x", "y", "width", "height"}

BLOCKED_CSS_VALUE_TOKENS = [
    "position:", "display:", "flex", "grid", "transform:", "z-index:",
    "overflow:", "visibility:", "pointer-events:",
]


def _assert_unit_interval(value: Any, label: str) -> None:
    if not isinstance(value, int | float) or not 0 <= value <= 1:
        raise ValueError(f"{label} must be a number between 0 and 1")


def _sanitize_style_tokens(tokens: dict[str, Any]) -> dict[str, Any]:
    """Remove non-whitelisted or dangerous CSS variable tokens."""
    out: dict[str, Any] = {}
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


def validate_slide_design_data(value: dict[str, Any], *, photo_id: str | None = None) -> dict[str, Any]:
    """Validate the subset of slide design JSON supported by v0.2."""

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
    value["styleTokens"] = _sanitize_style_tokens(tokens)

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
    for index, layer in enumerate(layers):
        if not isinstance(layer, dict):
            raise ValueError(f"layer {index} must be an object")
        layer_type = layer.get("type")
        if layer_type not in ALLOWED_LAYER_TYPES:
            raise ValueError(f"layer {index} has unsupported type: {layer_type}")

        if layer_type == "image":
            has_image_layer = True
            source = layer.get("source")
            if source not in ("preview", "thumbnail", "original"):
                raise ValueError(f"layer {index} image source must be preview/thumbnail/original")

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

    if not has_image_layer:
        raise ValueError("layers must include at least one image layer")

    return value
