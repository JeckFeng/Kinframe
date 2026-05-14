"""Build prompts for DeepSeek slide design generation."""

from __future__ import annotations

from app.services.ai.ollama_provider import VisionAnalysisResult

PROMPT_VERSION = "slide_design.v1"

ALLOWED_TEMPLATE_IDS = [
    "cinematic_fullscreen", "warm_memory", "minimal_white",
    "poetic_landscape", "magazine_left", "gallery_center",
    "dark_exhibition", "pet_portrait",
]
ALLOWED_LAYER_TYPES = ["shape", "image", "text", "timeline", "background", "mask", "texture", "vignette"]
ALLOWED_CSS_PREFIX = "--kf-"


def build_slide_design_prompt(
    *,
    photo_id: str,
    photo_category: str,
    user_message: str | None,
    taken_at_str: str,
    location_summary: str | None,
    vision_result: VisionAnalysisResult | None,
    prev_errors: list[str] | None,
) -> str:
    """Build the full prompt payload for DeepSeek slide design generation."""

    parts: list[str] = []

    parts.append(
        "You are a slide design AI for KinFrame, a family photo playback app. "
        "Generate a complete slide_design JSON for the photo described below. "
        "Output ONLY valid JSON — no explanation, no markdown outside the JSON."
    )
    parts.append(f"PROMPT_VERSION: {PROMPT_VERSION}")

    # ── Required output structure ─────────────────────────────────
    parts.append("## Output Structure (all fields required)")
    parts.append(
        'The JSON must have: photoId, templateId, templateParams, layers (non-empty array), '
        'styleTokens (object, keys must start with --kf-), renderPolicy (allowHtml: false, allowJavaScript: false), '
        'aiMeta (provider, model, promptVersion).'
    )

    # ── Templates ─────────────────────────────────────────────────
    parts.append("## Available Templates")
    parts.append(f"Choose from: {', '.join(ALLOWED_TEMPLATE_IDS)}")
    parts.append("  cinematic_fullscreen: dark (#111111), dramatic full-screen photo, for photography")
    parts.append("  warm_memory: warm (#f7f5ef), cozy family/life memories")
    parts.append("  minimal_white: clean white (#f7f5ef), for pet portraits / detailed subjects")
    parts.append("  poetic_landscape: dark (#0d1b2a), landscape with poetic caption placement")
    parts.append("  magazine_left: warm (#f7f5ef), magazine-style left photo + right text panel")
    parts.append("  gallery_center: dark (#1c2128), museum-style centered photo with wide margins")
    parts.append("  dark_exhibition: dark (#0a0a0f), dramatic exhibition with glowing photo frame")
    parts.append("  pet_portrait: warm (#2d1a1c), pet-focused with soft rounded photo frame")

    # ── Layer types ────────────────────────────────────────────────
    parts.append("## Available Layer Types")
    parts.append(f"Allowed types: {', '.join(ALLOWED_LAYER_TYPES)}")
    parts.append("  shape: decorative panels. Use fill, borderRadius, opacity in style.")
    parts.append("  image: the main photo. Source must be 'preview'. Use fit: 'contain' or 'cover'.")
    parts.append("  text: captions. Max 200 chars. Use color, fontSize (max 120px), textAlign in style.")
    parts.append("  timeline: date label. Use label, timeText, locationText, color, fontSize (max 120px).")
    parts.append("  background: full-screen gradient or solid color. Use gradient or color in style.")
    parts.append("  mask: semi-transparent overlay. Use color and opacity (0-1) in style. Max opacity 0.65.")
    parts.append("  texture: full-screen noise/grain overlay. REQUIRES fill.type: 'noise'. Use opacity and blendMode.")
    parts.append("  vignette: full-screen edge darkening. REQUIRES fill.type: 'radialGradient'. Use opacity. blendMode always 'multiply'.")

    # ── Design presets ─────────────────────────────────────────────
    parts.append("## Design Presets (use via presetRef)")
    parts.append("  Layer can reference a preset via presetRef field in any layer.")
    parts.append("  Available shadow presets: soft_elevation, dramatic_drop, warm_glow, inner_depth, classic_frame, subtle_lift")
    parts.append("  Available mask presets: left_fade, right_fade, bottom_fade, center_vignette, letterbox, corner_darken")
    parts.append("  Available lightOrb presets: warm_top_right, cool_top_left, golden_center, warm_bottom, cool_bottom_right, soft_pink_glow")
    parts.append("  Available timeline presets: minimal_line, soft_glow_line, year_mark, dotted_rhythm")
    parts.append("  Palette presets (via styleTokens): warm_amber_glow, misty_mountain_blue, golden_hour, soft_blush, forest_depth, ocean_dusk, autumn_charm, cool_mineral, spring_bloom, vintage_sepia, midnight_cinema, morning_dew")
    parts.append("## Structured Fill & Shadow Models")
    parts.append("  Fill object: { type: 'solid'|'linearGradient'|'radialGradient'|'imageBlur'|'noise', color?, angle?, center?, radius?, stops? }")
    parts.append("  Gradient stops: array of { color: '#RRGGBB', opacity: 0-1, position: 0-1 }, 2-5 stops required")
    parts.append("  Shadow object: { enabled: true, type: 'soft'|'dramatic'|'glow'|'inner', x, y, blur (max 120), spread, color, opacity }")
    parts.append("## Quality Guidelines")
    parts.append("  - Text captions must NOT overlap the center 60% area of the photo")
    parts.append("  - Text color must have sufficient contrast against background (WCAG AA: 4.5:1)")
    parts.append("  - Mask layers: opacity must be ≤ 0.65")
    parts.append("  - Total layers must not exceed template maxExtraLayers + 1 base layer")
    parts.append("  - Gradient stops: always 2-5 stops")
    parts.append("  - Structure your design for high quality score (≥3/5 checks must pass)")
    parts.append("## Scoped CSS (optional)")
    parts.append("  You may include a 'scopedCss' string in styleTokens with safe CSS rules.")
    parts.append("  Only use selectors: .kf-slide, .kf-layer, .kf-photo-layer, .kf-text-layer, .kf-shape-layer, .kf-mask-layer, .kf-timeline-layer, .kf-caption, .kf-meta, .kf-photo-frame, .kf-caption-panel")
    parts.append("  Only use properties: color, background-*, opacity, box-shadow, text-shadow, filter, backdrop-filter, mix-blend-mode, border-*, border-radius, letter-spacing, line-height, font-*, text-*, transition-*, animation-*, transform, clip-path, mask-*")
    parts.append("  NEVER use: position, display, flex, grid, z-index, overflow, visibility, pointer-events, url(), @import, javascript:")
    parts.append("## Constraints")
    parts.append("  rect: {x, y, width, height} all between 0.0 and 1.0, width and height must be > 0")
    parts.append("  zIndex: integer 0-100")
    parts.append("  At least 1 image layer required")
    parts.append("  No html, script, or executable fields in layers")
    parts.append("  styleTokens keys must start with --kf-")

    # ── CSS whitelist ──────────────────────────────────────────────
    parts.append("## CSS Variable Whitelist")
    parts.append("  All styleTokens keys must have prefix: --kf-")
    parts.append("  Example: --kf-background-color, --kf-text-color, --kf-accent-color")
    parts.append("  Do NOT use position:, display:, flex, grid, transform:, z-index:,")
    parts.append("  overflow:, visibility:, pointer-events: in styleToken values.")
    parts.append("  styleTokens object may also include optional 'scopedCss' string with safe CSS rules.")

    # ── Photo context ──────────────────────────────────────────────
    parts.append("## Photo Context")
    parts.append(f"  photoId: {photo_id}")
    parts.append(f"  category: {photo_category}")
    parts.append(f"  taken_at: {taken_at_str}")

    if user_message:
        parts.append(f"  user_message: \"{user_message}\"")
        parts.append(
            "  IMPORTANT: The user_message IS the caption. Do NOT rewrite, change, or replace it. "
            "Use the exact user_message text for any text layer with role 'caption'."
        )
    else:
        parts.append("  user_message: (none — do NOT invent a caption if there is no user_message)")

    if location_summary:
        parts.append(f"  location: {location_summary}")
    else:
        parts.append("  location: unknown")

    # ── Vision analysis ────────────────────────────────────────────
    if vision_result:
        parts.append("## Vision Analysis (from Ollama)")
        parts.append(f"  subject: {vision_result.subject or 'unknown'}")
        parts.append(f"  scene: {vision_result.scene or 'unknown'}")
        parts.append(f"  mood: {', '.join(vision_result.mood) if vision_result.mood else 'unknown'}")
        parts.append(f"  dominant_colors: {', '.join(vision_result.dominant_colors) if vision_result.dominant_colors else 'unknown'}")
        parts.append(f"  environment: {vision_result.environment or 'unknown'}")
        parts.append(f"  suggested_category: {vision_result.suggested_category or 'unknown'}")
        parts.append(f"  quality: {vision_result.quality or 'unknown'}")
        if user_message is None:
            parts.append(
                "  NOTE: Use visual analysis for scene/layout context ONLY. Do NOT invent "
                "image descriptions or captions — there is no user_message, so do not write "
                "what the photo subject looks like in any text layer."
            )
    else:
        parts.append("## Vision Analysis")
        parts.append(
            "  No visual analysis available. Do NOT describe the image subject, mood, scene, "
            "weather, or colors. Focus layout on orientation, timing, and location only."
        )

    # ── Previous errors (retry correction) ────────────────────────
    if prev_errors:
        parts.append("## Previous Validation Errors (Fix These)")
        parts.append("  The previous output was rejected. Fix ONLY these errors and output complete JSON:")
        for err in prev_errors:
            parts.append(f"  - {err}")

    parts.append(
        "\nGenerate the complete slide_design JSON now. Remember: output ONLY the JSON object, "
        "no markdown fences, no explanation."
    )
    return "\n".join(parts)
