"""Minimal validation for KinFrame slide design JSON."""

from typing import Any

ALLOWED_TEMPLATE_IDS = {"cinematic_fullscreen", "warm_memory", "minimal_white"}
ALLOWED_LAYER_TYPES = {"shape", "image", "text", "timeline"}
REQUIRED_DESIGN_KEYS = {"photoId", "templateId", "templateParams", "layers", "styleTokens", "renderPolicy"}
RECT_KEYS = {"x", "y", "width", "height"}


def _assert_unit_interval(value: Any, label: str) -> None:
    if not isinstance(value, int | float) or not 0 <= value <= 1:
        raise ValueError(f"{label} must be a number between 0 and 1")


def validate_slide_design_data(value: dict[str, Any]) -> dict[str, Any]:
    """Validate the subset of slide design JSON supported by v0.1 fallback."""

    missing = REQUIRED_DESIGN_KEYS - set(value)
    if missing:
        raise ValueError(f"slide design is missing required keys: {sorted(missing)}")
    if value["templateId"] not in ALLOWED_TEMPLATE_IDS:
        raise ValueError("templateId is not supported")
    if not isinstance(value["templateParams"], dict):
        raise ValueError("templateParams must be an object")
    if not isinstance(value["styleTokens"], dict):
        raise ValueError("styleTokens must be an object")
    for token in value["styleTokens"]:
        if not token.startswith("--kf-"):
            raise ValueError("styleTokens only allows --kf-* CSS variables")

    render_policy = value["renderPolicy"]
    if not isinstance(render_policy, dict):
        raise ValueError("renderPolicy must be an object")
    if render_policy.get("allowHtml") is not False or render_policy.get("allowJavaScript") is not False:
        raise ValueError("fallback slide designs cannot allow HTML or JavaScript")

    layers = value["layers"]
    if not isinstance(layers, list) or not layers:
        raise ValueError("layers must be a non-empty list")
    for index, layer in enumerate(layers):
        if not isinstance(layer, dict):
            raise ValueError(f"layer {index} must be an object")
        if layer.get("type") not in ALLOWED_LAYER_TYPES:
            raise ValueError(f"layer {index} has unsupported type")
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
    return value
