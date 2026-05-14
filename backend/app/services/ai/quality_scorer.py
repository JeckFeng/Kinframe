"""Design quality scoring for AI-generated slide designs.

Five quality checks:
1. Text occlusion: caption must not overlap photo center 60%
2. Contrast: text vs background must meet WCAG AA (4.5:1)
3. Mask intensity: no mask opacity > 0.65
4. Layer count: total ≤ maxExtraLayers + base layers
5. Gradient stops: 2-5 stops

Composite score ≥ threshold → accept; < threshold → trigger retry.
"""

from __future__ import annotations

from dataclasses import dataclass

QUALITY_THRESHOLD = 3  # Must score ≥ 3 out of 5 to accept
WCAG_AA_CONTRAST_RATIO = 4.5


@dataclass
class QualityReport:
    total_score: int = 0
    passed: bool = False
    text_occlusion_pass: bool = True
    contrast_pass: bool = True
    mask_intensity_pass: bool = True
    layer_count_pass: bool = True
    gradient_stops_pass: bool = True
    failures: list[str] | None = None

    def __post_init__(self):
        if self.failures is None:
            self.failures = []


def _relative_luminance(hex_color: str) -> float:
    """Compute WCAG relative luminance from a hex color string."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)
    r = int(hex_color[0:2], 16) / 255.0
    g = int(hex_color[2:4], 16) / 255.0
    b = int(hex_color[4:6], 16) / 255.0

    def _linearize(c: float) -> float:
        if c <= 0.04045:
            return c / 12.92
        return ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * _linearize(r) + 0.7152 * _linearize(g) + 0.0722 * _linearize(b)


def _contrast_ratio(bg: str, fg: str) -> float:
    """Compute WCAG contrast ratio between two hex colors."""
    l1 = _relative_luminance(bg)
    l2 = _relative_luminance(fg)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def _rects_overlap(a: dict, b: dict) -> bool:
    """Check if two normalized (0-1) rectangles overlap."""
    return not (
        a["x"] + a["width"] <= b["x"]
        or b["x"] + b["width"] <= a["x"]
        or a["y"] + a["height"] <= b["y"]
        or b["y"] + b["height"] <= a["y"]
    )


# ── Individual checks ────────────────────────────────────────────────────────


def check_text_occlusion(
    photo_rect: dict | None,
    caption_rect: dict | None,
) -> bool:
    """Caption text must not overlap the center 60% of the photo.

    Center 60% region: inner 60% of photo rect (20% margin on each side).
    """
    if photo_rect is None or caption_rect is None:
        return True

    # Compute the center 60% region of the photo
    pw = photo_rect.get("width", 0)
    ph = photo_rect.get("height", 0)
    px = photo_rect.get("x", 0)
    py = photo_rect.get("y", 0)

    center = {
        "x": px + pw * 0.2,
        "y": py + ph * 0.2,
        "width": pw * 0.6,
        "height": ph * 0.6,
    }

    return not _rects_overlap(center, caption_rect)


def check_contrast_wcag_aa(
    bg_color: str | None,
    text_color: str | None,
) -> bool:
    """Verify text-background contrast meets WCAG AA (≥ 4.5:1)."""
    if not bg_color or not text_color:
        return True
    try:
        ratio = _contrast_ratio(bg_color, text_color)
        return ratio >= WCAG_AA_CONTRAST_RATIO
    except (ValueError, IndexError):
        return True  # Skip if color parsing fails


def check_mask_intensity(max_mask_opacity: float | None) -> bool:
    """No mask layer should have opacity > 0.65."""
    if max_mask_opacity is None:
        return True
    return max_mask_opacity <= 0.65


def check_layer_count(
    total_layers: int,
    *,
    max_extra_layers: int = 4,
    base_layers: int = 1,
) -> bool:
    """Total layers must be ≤ base_layers + max_extra_layers."""
    return total_layers <= base_layers + max_extra_layers


def check_gradient_stops(stops: list | None) -> bool:
    """Gradient must have 2-5 stops."""
    if stops is None:
        return True
    if not isinstance(stops, list):
        return False
    return 2 <= len(stops) <= 5


# ── Composite scoring ────────────────────────────────────────────────────────


def score_design_quality(
    design: dict,
    *,
    max_extra_layers: int = 4,
    base_layers: int = 1,
) -> QualityReport:
    """Run all quality checks and return a composite score.

    Returns a QualityReport with score 0-5 and pass/fail per check.
    """
    failures: list[str] = []
    layers = design.get("layers", [])
    style_tokens = design.get("styleTokens", {})

    # Extract photo and caption rects
    photo_rect = None
    caption_rect = None
    max_mask_opacity = None
    all_gradient_stops_ok = True

    for layer in layers:
        ltype = layer.get("type")
        if ltype == "image":
            photo_rect = layer.get("rect")
        elif ltype == "text":
            role = layer.get("role", "")
            if "caption" in role or ltype == "text":
                caption_rect = layer.get("rect") if caption_rect is None else caption_rect

        # Track mask opacity
        if ltype == "mask":
            style = layer.get("style", {}) or {}
            opacity = style.get("opacity", 0.5)
            if max_mask_opacity is None or opacity > max_mask_opacity:
                max_mask_opacity = opacity

        # Check gradient stops in fills
        fill = layer.get("fill")
        if fill and fill.get("type") in ("linearGradient", "radialGradient"):
            stops = fill.get("stops")
            if stops is not None and not check_gradient_stops(stops):
                all_gradient_stops_ok = False

    # 1. Text occlusion
    text_ok = check_text_occlusion(photo_rect, caption_rect)
    if not text_ok:
        failures.append("Text caption overlaps photo center 60% area")

    # 2. Contrast
    bg = style_tokens.get("--kf-background-color") if isinstance(style_tokens, dict) else None
    fg = style_tokens.get("--kf-text-color") if isinstance(style_tokens, dict) else None
    contrast_ok = check_contrast_wcag_aa(bg, fg)
    if not contrast_ok:
        failures.append(f"Text contrast insufficient: {fg} on {bg}")

    # 3. Mask intensity
    mask_ok = check_mask_intensity(max_mask_opacity)
    if not mask_ok:
        failures.append(f"Mask opacity {max_mask_opacity} exceeds max 0.65")

    # 4. Layer count
    layers_ok = check_layer_count(len(layers), max_extra_layers=max_extra_layers, base_layers=base_layers)
    if not layers_ok:
        failures.append(f"Layer count {len(layers)} exceeds max {base_layers + max_extra_layers}")

    # 5. Gradient stops
    grad_ok = all_gradient_stops_ok
    if not grad_ok:
        failures.append("Gradient stops out of range (must be 2-5)")

    score = sum([text_ok, contrast_ok, mask_ok, layers_ok, grad_ok])

    return QualityReport(
        total_score=score,
        passed=score >= QUALITY_THRESHOLD,
        text_occlusion_pass=text_ok,
        contrast_pass=contrast_ok,
        mask_intensity_pass=mask_ok,
        layer_count_pass=layers_ok,
        gradient_stops_pass=grad_ok,
        failures=failures,
    )
