"""Tests for enhanced AI Prompt Builder — dynamic config-driven prompts."""

import json
from pathlib import Path

import pytest

from app.services.ai.slide_design_prompt import (
    ALLOWED_TEMPLATE_IDS,
    ALLOWED_LAYER_TYPES,
    build_slide_design_prompt,
)


def _config_path(name: str) -> Path:
    return Path(__file__).parent.parent.parent / "frontend" / "app" / "slide-renderer" / "configs" / name


class TestPromptTemplateCoverage:
    def test_includes_all_8_templates(self):
        """Prompt must list all 8 template IDs (up from 3 in v0.2)."""
        assert len(ALLOWED_TEMPLATE_IDS) == 8
        expected = {
            "cinematic_fullscreen", "warm_memory", "minimal_white",
            "poetic_landscape", "magazine_left", "gallery_center",
            "dark_exhibition", "pet_portrait",
        }
        assert set(ALLOWED_TEMPLATE_IDS) == expected

    def test_includes_all_layer_types(self):
        """Prompt must include all layer types including texture and vignette."""
        assert "texture" in ALLOWED_LAYER_TYPES
        assert "vignette" in ALLOWED_LAYER_TYPES
        assert "shape" in ALLOWED_LAYER_TYPES
        assert "mask" in ALLOWED_LAYER_TYPES
        assert len(ALLOWED_LAYER_TYPES) >= 8


class TestBuildSlideDesignPrompt:
    def test_includes_all_templates_in_output(self):
        """Generated prompt should mention all 8 templates."""
        prompt = build_slide_design_prompt(
            photo_id="p1", photo_category="life",
            user_message=None, taken_at_str="2024-01-15T10:00:00Z",
            location_summary=None, vision_result=None, prev_errors=None,
        )
        for tid in ALLOWED_TEMPLATE_IDS:
            assert tid in prompt, f"Template {tid} missing from prompt"

    def test_includes_all_layer_types_in_output(self):
        """Generated prompt should describe all layer types."""
        prompt = build_slide_design_prompt(
            photo_id="p1", photo_category="life",
            user_message=None, taken_at_str="2024-01-15T10:00:00Z",
            location_summary=None, vision_result=None, prev_errors=None,
        )
        for lt in ALLOWED_LAYER_TYPES:
            assert lt in prompt.lower(), f"Layer type {lt} missing from prompt"

    def test_includes_preset_references(self):
        """Prompt should mention that presets are available via presetRef."""
        prompt = build_slide_design_prompt(
            photo_id="p1", photo_category="life",
            user_message=None, taken_at_str="2024-01-15T10:00:00Z",
            location_summary=None, vision_result=None, prev_errors=None,
        )
        assert "presetRef" in prompt

    def test_includes_caption_policy(self):
        """Prompt must explain caption policy rules."""
        prompt = build_slide_design_prompt(
            photo_id="p1", photo_category="life",
            user_message=None, taken_at_str="2024-01-15T10:00:00Z",
            location_summary=None, vision_result=None, prev_errors=None,
        )
        assert "caption" in prompt.lower()
        assert "user_message" in prompt

    def test_enforces_json_only_output(self):
        """Prompt must require JSON-only output."""
        prompt = build_slide_design_prompt(
            photo_id="p1", photo_category="life",
            user_message=None, taken_at_str="2024-01-15T10:00:00Z",
            location_summary=None, vision_result=None, prev_errors=None,
        )
        assert "JSON" in prompt
        assert "json" in prompt.lower()

    def test_includes_quality_scoring_hint(self):
        """Prompt should hint at quality expectations to guide AI output."""
        prompt = build_slide_design_prompt(
            photo_id="p1", photo_category="life",
            user_message=None, taken_at_str="2024-01-15T10:00:00Z",
            location_summary=None, vision_result=None, prev_errors=None,
        )
        assert "quality" in prompt.lower()

    def test_user_message_included_and_prioritized(self):
        """When user_message exists, prompt must instruct to use it as-is."""
        prompt = build_slide_design_prompt(
            photo_id="p1", photo_category="life",
            user_message="My exact caption text",
            taken_at_str="2024-01-15T10:00:00Z",
            location_summary=None, vision_result=None, prev_errors=None,
        )
        assert "My exact caption text" in prompt
        assert "NOT rewrite" in prompt or "NOT invent" in prompt

    def test_no_user_message_means_no_caption_invention(self):
        """When no user_message, prompt must forbid inventing captions."""
        prompt = build_slide_design_prompt(
            photo_id="p1", photo_category="life",
            user_message=None, taken_at_str="2024-01-15T10:00:00Z",
            location_summary=None, vision_result=None, prev_errors=None,
        )
        assert "do not invent" in prompt.lower() or "do NOT invent" in prompt or "no caption" in prompt.lower()
