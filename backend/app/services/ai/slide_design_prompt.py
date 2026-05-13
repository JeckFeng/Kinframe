"""Build prompts for DeepSeek slide design generation."""

from __future__ import annotations

from app.services.ai.ollama_provider import VisionAnalysisResult

PROMPT_VERSION = "slide_design.v1"

ALLOWED_TEMPLATE_IDS = ["cinematic_fullscreen", "warm_memory", "minimal_white"]
ALLOWED_LAYER_TYPES = ["shape", "image", "text", "timeline", "background", "mask"]
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
    parts.append("  cinematic_fullscreen: dark background (#111111), dramatic, for photography/travel")
    parts.append("  warm_memory: light warm background (#f7f5ef), for family/life photos")
    parts.append("  minimal_white: clean white background (#f7f5ef), for pet portraits / detailed subjects")

    # ── Layer types ────────────────────────────────────────────────
    parts.append("## Available Layer Types")
    parts.append(f"Allowed types: {', '.join(ALLOWED_LAYER_TYPES)}")
    parts.append("  shape: decorative panels. Use fill, borderRadius, opacity in style.")
    parts.append("  image: the main photo. Source must be 'preview'. Use fit: 'contain' or 'cover'.")
    parts.append("  text: captions. Max 200 chars. Use color, fontSize (max 120px), textAlign in style.")
    parts.append("  timeline: date label. Use label, timeText, locationText, color, fontSize (max 120px).")
    parts.append("  background: full-screen gradient or solid color. Use gradient or color in style.")
    parts.append("  mask: semi-transparent overlay. Use color and opacity (0-1) in style.")
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
