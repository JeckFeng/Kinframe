"""Tests for CSS Sanitizer — whitelist-based scoped CSS security."""

import pytest

from app.services.scoped_css import (
    CSS_SANITIZER_ALLOWED_SELECTORS,
    CSS_SANITIZER_ALLOWED_PROPERTIES,
    sanitize_scoped_css,
    SanitizeResult,
)


class TestSelectorWhitelist:
    def test_allows_valid_kinframe_selectors(self):
        """All KinFrame-specific selectors should be in the whitelist."""
        for sel in [".kf-slide", ".kf-layer", ".kf-photo-layer", ".kf-text-layer",
                     ".kf-shape-layer", ".kf-mask-layer", ".kf-timeline-layer",
                     ".kf-caption", ".kf-meta", ".kf-photo-frame", ".kf-caption-panel"]:
            assert sel in CSS_SANITIZER_ALLOWED_SELECTORS, f"{sel} must be allowed"

    def test_rejects_forbidden_selectors(self):
        """Global/structural selectors must not be in the whitelist."""
        forbidden = ["html", "body", "#app", "*", "script", "iframe", "input", "button"]
        for sel in forbidden:
            assert sel not in CSS_SANITIZER_ALLOWED_SELECTORS, f"{sel} must be forbidden"


class TestPropertyWhitelist:
    def test_allows_visual_properties(self):
        """Visual-only CSS properties should be in the whitelist."""
        allowed = ["color", "background-color", "opacity", "box-shadow",
                    "border-radius", "font-size", "text-align", "filter", "transform"]
        for prop in allowed:
            assert prop in CSS_SANITIZER_ALLOWED_PROPERTIES, f"{prop} must be allowed"

    def test_rejects_layout_properties(self):
        """Layout-breaking properties must not be in the whitelist."""
        forbidden = ["position", "top", "left", "width", "height",
                      "z-index", "display", "flex", "overflow", "visibility"]
        for prop in forbidden:
            assert prop not in CSS_SANITIZER_ALLOWED_PROPERTIES, f"{prop} must be forbidden"


class TestSanitizeScopedCss:
    def test_passes_valid_simple_css(self):
        """A single valid rule should pass through unchanged."""
        css = ".kf-caption { color: #ffffff; }"
        result = sanitize_scoped_css(css)
        assert result.is_valid
        assert ".kf-caption" in result.safe_css
        assert "color" in result.safe_css

    def test_passes_multiple_valid_rules(self):
        """Multiple valid rules should all pass through."""
        css = """.kf-caption { color: #fff; font-size: 14px; }
.kf-photo-layer { filter: brightness(1.02); border-radius: 8px; }"""
        result = sanitize_scoped_css(css)
        assert result.is_valid
        assert result.safe_css

    def test_strips_forbidden_selector(self):
        """Rules with forbidden selectors should be removed."""
        css = ".kf-caption { color: #fff; } body { background: red; }"
        result = sanitize_scoped_css(css)
        assert result.is_valid
        assert ".kf-caption" in result.safe_css
        assert "body" not in result.safe_css

    def test_strips_forbidden_property(self):
        """Forbidden properties should be removed from otherwise-valid rules."""
        css = ".kf-caption { color: #fff; position: fixed; }"
        result = sanitize_scoped_css(css)
        assert result.is_valid
        assert "color" in result.safe_css
        assert "position" not in result.safe_css

    def test_rejects_import_directive(self):
        """@import should make the entire CSS block invalid."""
        css = '.kf-caption { color: #fff; } @import url("evil.css");'
        result = sanitize_scoped_css(css)
        assert not result.is_valid

    def test_rejects_javascript_url(self):
        """javascript: URLs should make the entire block invalid."""
        css = ".kf-caption { background: javascript:alert(1); }"
        result = sanitize_scoped_css(css)
        assert not result.is_valid

    def test_rejects_expression(self):
        """CSS expression() should make the entire block invalid."""
        css = ".kf-caption { width: expression(alert(1)); }"
        result = sanitize_scoped_css(css)
        assert not result.is_valid

    def test_rejects_url_function(self):
        """url() with external resources should be blocked."""
        css = '.kf-caption { background: url("http://evil.com/x.png"); }'
        result = sanitize_scoped_css(css)
        assert not result.is_valid

    def test_handles_empty_css(self):
        """Empty CSS string should produce empty safe CSS but still be valid."""
        result = sanitize_scoped_css("")
        assert result.is_valid
        assert result.safe_css == ""

    def test_handles_only_forbidden_rules(self):
        """CSS with only forbidden selectors should produce empty safe CSS."""
        css = "body { background: red; } html { opacity: 0; }"
        result = sanitize_scoped_css(css)
        assert result.is_valid
        assert result.safe_css == ""

    def test_strips_comma_selector_with_forbidden_part(self):
        """Comma selectors containing forbidden parts should be rejected."""
        css = ".kf-caption, body { color: #fff; }"
        result = sanitize_scoped_css(css)
        assert result.is_valid
        assert "body" not in result.safe_css
        # The rule should be filtered entirely since one selector part is forbidden
        assert ".kf-caption" not in result.safe_css

    def test_preserves_data_attribute_selectors(self):
        """Selectors with data attributes on allowed bases should pass."""
        css = '.kf-slide[data-template="dark"] { color: #fff; }'
        result = sanitize_scoped_css(css)
        assert result.is_valid
        assert "kf-slide" in result.safe_css

    def test_rejects_parent_escape_selectors(self):
        """Selectors that escape the slide scope (parent references) should be blocked."""
        # :has(), :is() with external references
        css = ".kf-slide:has(body.dark-mode) { color: #fff; }"
        result = sanitize_scoped_css(css)
        # The :has() pseudo-class containing forbidden selector should strip the rule
        assert result.is_valid
        assert "body" not in result.safe_css

    def test_warns_on_rejected_rules(self):
        """Rejected rules should appear in warnings list."""
        css = "body { background: red; } .kf-caption { color: #fff; }"
        result = sanitize_scoped_css(css)
        assert result.is_valid
        assert len(result.warnings) > 0
