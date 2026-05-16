"""Build prompts for DeepSeek slide design generation and granular regeneration."""

from __future__ import annotations

import json
from typing import Any

from app.schemas.slide_design_assets import (
    get_layer_types,
    get_template_definition,
    get_template_definitions,
    get_template_ids,
    load_ai_css_whitelist,
    load_design_presets,
)
from app.services.ai.css_sanitizer import (
    CSS_SANITIZER_ALLOWED_PROPERTIES,
    CSS_SANITIZER_ALLOWED_SELECTORS,
)
from app.services.ai.ollama_provider import VisionAnalysisResult

PROMPT_VERSION = "slide_design.v1"
CAPTION_PROMPT_VERSION = "caption_regen.v1"
TEMPLATE_PROMPT_VERSION = "template_regen.v1"
CSS_PROMPT_VERSION = "css_regen.v1"

ALLOWED_TEMPLATE_IDS = get_template_ids()
ALLOWED_LAYER_TYPES = get_layer_types()
ALLOWED_CSS_PREFIX = load_ai_css_whitelist().get("variablePrefix", "--kf-")
PRESETS = load_design_presets()


def _dump_json(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def _append_common_context(
    parts: list[str],
    *,
    photo_id: str,
    photo_category: str,
    user_message: str | None,
    ai_caption_enabled: bool,
    taken_at_str: str,
    location_summary: str | None,
    vision_result: VisionAnalysisResult | None,
    prev_errors: list[str] | None,
) -> None:
    parts.append("## Photo Context")
    parts.append(f"photoId: {photo_id}")
    parts.append(f"category: {photo_category}")
    parts.append(f"taken_at: {taken_at_str}")
    parts.append(f"location: {location_summary or 'unknown'}")

    if user_message:
        parts.append(f"user_message: {json.dumps(user_message, ensure_ascii=False)}")
        parts.append("If you output a caption layer, use the exact user_message text. Do NOT rewrite, replace, or summarize it.")
    elif ai_caption_enabled:
        parts.append("user_message: none")
        parts.append(
            "AI caption is enabled. Generate exactly one short neutral visible caption in Chinese "
            "(10-35 characters) based only on visible scene and known context. "
            "Do not invent names, precise locations, dates, identities, or relationships. "
            "Place that text in a caption text layer with role=caption."
        )
    else:
        parts.append("user_message: none")
        parts.append("AI caption is disabled. Do not invent a visible caption and do not output a caption text layer.")

    if vision_result:
        parts.append("## Vision Analysis")
        parts.append(f"subject: {vision_result.subject or 'unknown'}")
        parts.append(f"scene: {vision_result.scene or 'unknown'}")
        parts.append(f"mood: {', '.join(vision_result.mood) if vision_result.mood else 'unknown'}")
        parts.append(
            f"dominant_colors: {', '.join(vision_result.dominant_colors) if vision_result.dominant_colors else 'unknown'}"
        )
        parts.append(f"environment: {vision_result.environment or 'unknown'}")
        parts.append(f"suggested_category: {vision_result.suggested_category or 'unknown'}")
        parts.append(f"quality: {vision_result.quality or 'unknown'}")
    else:
        parts.append("## Vision Analysis")
        parts.append("No visual analysis available. Do not describe unseen subject details.")

    if prev_errors:
        parts.append("## Previous Validation Errors")
        parts.append("The previous output was rejected. Fix these errors in the next JSON output:")
        for err in prev_errors:
            parts.append(f"- {err}")


def _append_template_catalog(parts: list[str]) -> None:
    parts.append("## Templates")
    for template in get_template_definitions():
        parts.append(
            f"- {template['id']}: {template.get('description', template['name'])} "
            f"(preferredCategories={template.get('preferredCategories', [])}, "
            f"allowedLayerTypes={template.get('allowedLayerTypes', [])}, "
            f"maxExtraLayers={template.get('maxExtraLayers', 0)})"
        )


def _append_design_capabilities(parts: list[str]) -> None:
    presets_summary = {
        "palettes": sorted(PRESETS.get("palettes", {}).keys()),
        "shadows": sorted(PRESETS.get("shadows", {}).keys()),
        "masks": sorted(PRESETS.get("masks", {}).keys()),
        "lightOrbs": sorted(PRESETS.get("lightOrbs", {}).keys()),
        "timelines": sorted(PRESETS.get("timelines", {}).keys()),
        "fonts": sorted(PRESETS.get("fonts", {}).keys()),
    }
    parts.append("## Layer Types")
    parts.append(", ".join(ALLOWED_LAYER_TYPES))
    parts.append("At least one image layer is required. image.source must be preview/thumbnail/original.")
    parts.append("text.content <= 200 chars. rect values must be 0..1 and width/height > 0. zIndex 0..100.")
    parts.append("renderPolicy.allowHtml=false and renderPolicy.allowJavaScript=false.")
    parts.append("## Presets")
    parts.append(_dump_json(presets_summary))
    parts.append("You may reference curated layer presets by setting presetRef on a layer when it helps.")
    parts.append("## CSS")
    parts.append(f"styleTokens CSS variable keys must start with {ALLOWED_CSS_PREFIX}")
    parts.append(
        "Allowed selectors: "
        + ", ".join(sorted(CSS_SANITIZER_ALLOWED_SELECTORS))
    )
    parts.append(
        "Allowed CSS properties: "
        + ", ".join(sorted(CSS_SANITIZER_ALLOWED_PROPERTIES))
    )
    parts.append("scopedCss is optional and must be safe scoped CSS only. No html, script, url(), @import, javascript:.")
    parts.append("## Quality Rules")
    parts.append("Text captions must not overlap the center 60% of the photo.")
    parts.append("Text/background contrast should meet WCAG AA (4.5:1).")
    parts.append("Mask opacity must stay <= 0.65. Gradient stops must be 2-5. Respect template maxExtraLayers.")


def build_slide_design_prompt(
    *,
    photo_id: str,
    photo_category: str,
    user_message: str | None,
    ai_caption_enabled: bool,
    taken_at_str: str,
    location_summary: str | None,
    vision_result: VisionAnalysisResult | None,
    prev_errors: list[str] | None,
) -> str:
    """Build the full prompt payload for DeepSeek slide design generation."""

    parts: list[str] = [
        "You are a slide design AI for KinFrame.",
        "Output ONLY one valid JSON object for a complete slide design. No markdown, no explanation.",
        f"PROMPT_VERSION: {PROMPT_VERSION}",
        "## Output JSON",
        (
            'Required keys: photoId, templateId, templateParams, layers, styleTokens, renderPolicy. '
            'styleTokens may contain --kf-* CSS variables and optional scopedCss. '
            'aiMeta should include provider, model, promptVersion.'
        ),
    ]
    _append_template_catalog(parts)
    _append_design_capabilities(parts)
    _append_common_context(
        parts,
        photo_id=photo_id,
        photo_category=photo_category,
        user_message=user_message,
        ai_caption_enabled=ai_caption_enabled,
        taken_at_str=taken_at_str,
        location_summary=location_summary,
        vision_result=vision_result,
        prev_errors=prev_errors,
    )
    parts.append("Generate the complete slide design JSON now.")
    return "\n".join(parts)


def build_caption_regeneration_prompt(
    *,
    photo_id: str,
    photo_category: str,
    user_message: str | None,
    taken_at_str: str,
    location_summary: str | None,
    vision_result: VisionAnalysisResult | None,
    active_design: dict[str, Any],
    prev_errors: list[str] | None,
) -> str:
    parts = [
        "You regenerate only the AI caption for KinFrame.",
        "Output ONLY JSON: {\"caption\": string|null}. No markdown, no explanation.",
        f"PROMPT_VERSION: {CAPTION_PROMPT_VERSION}",
        "Do not output any slide design fields.",
        f"current_design: {_dump_json(active_design)}",
    ]
    _append_common_context(
        parts,
        photo_id=photo_id,
        photo_category=photo_category,
        user_message=user_message,
        ai_caption_enabled=True,
        taken_at_str=taken_at_str,
        location_summary=location_summary,
        vision_result=vision_result,
        prev_errors=prev_errors,
    )
    parts.append("If user_message exists, return it unchanged as caption. If there is no user_message, return a short neutral caption or null.")
    return "\n".join(parts)


def build_template_regeneration_prompt(
    *,
    photo_id: str,
    photo_category: str,
    user_message: str | None,
    ai_caption_enabled: bool,
    taken_at_str: str,
    location_summary: str | None,
    vision_result: VisionAnalysisResult | None,
    active_design: dict[str, Any],
    prev_errors: list[str] | None,
) -> str:
    parts = [
        "You regenerate only the template selection for a KinFrame slide.",
        "Output ONLY JSON: {\"templateId\": string, \"templateParams\": object}. No markdown.",
        f"PROMPT_VERSION: {TEMPLATE_PROMPT_VERSION}",
        f"current_design: {_dump_json(active_design)}",
        "Keep caption text, layer contents, layer order, and styleTokens unchanged. Only choose a better template and templateParams.",
    ]
    _append_template_catalog(parts)
    _append_common_context(
        parts,
        photo_id=photo_id,
        photo_category=photo_category,
        user_message=user_message,
        ai_caption_enabled=ai_caption_enabled,
        taken_at_str=taken_at_str,
        location_summary=location_summary,
        vision_result=vision_result,
        prev_errors=prev_errors,
    )
    return "\n".join(parts)


def build_css_regeneration_prompt(
    *,
    photo_id: str,
    photo_category: str,
    user_message: str | None,
    ai_caption_enabled: bool,
    taken_at_str: str,
    location_summary: str | None,
    vision_result: VisionAnalysisResult | None,
    active_design: dict[str, Any],
    prev_errors: list[str] | None,
) -> str:
    parts = [
        "You regenerate only the style tokens for a KinFrame slide.",
        "Output ONLY JSON: {\"styleTokens\": object}. styleTokens may contain --kf-* variables and optional scopedCss. No markdown.",
        f"PROMPT_VERSION: {CSS_PROMPT_VERSION}",
        f"current_design: {_dump_json(active_design)}",
        "Keep templateId, templateParams, layers, and caption text unchanged. Only improve colors, typography tokens, shadow/filter tokens, and safe scopedCss.",
    ]
    _append_design_capabilities(parts)
    _append_common_context(
        parts,
        photo_id=photo_id,
        photo_category=photo_category,
        user_message=user_message,
        ai_caption_enabled=ai_caption_enabled,
        taken_at_str=taken_at_str,
        location_summary=location_summary,
        vision_result=vision_result,
        prev_errors=prev_errors,
    )
    return "\n".join(parts)


def get_default_template_params(template_id: str) -> dict[str, Any]:
    template = get_template_definition(template_id)
    if not template:
        return {}
    params = template.get("defaultParams", {})
    return params if isinstance(params, dict) else {}
