"""Tests for Design Quality Scorer — 5 quality checks + retry logic."""

import pytest

from app.services.ai.quality_scorer import (
    QualityReport,
    check_contrast_wcag_aa,
    check_gradient_stops,
    check_layer_count,
    check_mask_intensity,
    check_text_occlusion,
    score_design_quality,
)


class TestTextOcclusionCheck:
    def test_passes_when_caption_below_photo_center(self):
        """Caption at bottom (y=0.85) should not overlap photo center 60%."""
        photo_rect = {"x": 0.05, "y": 0.05, "width": 0.9, "height": 0.7}
        caption_rect = {"x": 0.05, "y": 0.85, "width": 0.9, "height": 0.08}
        assert check_text_occlusion(photo_rect, caption_rect) is True

    def test_fails_when_caption_overlaps_photo_center(self):
        """Caption overlapping photo center 60% should fail."""
        photo_rect = {"x": 0.05, "y": 0.05, "width": 0.9, "height": 0.9}
        caption_rect = {"x": 0.05, "y": 0.45, "width": 0.9, "height": 0.1}
        assert check_text_occlusion(photo_rect, caption_rect) is False

    def test_returns_true_without_caption_rect(self):
        """No caption layer should pass by default."""
        photo_rect = {"x": 0, "y": 0, "width": 1, "height": 1}
        assert check_text_occlusion(photo_rect, None) is True

    def test_returns_true_without_photo_rect(self):
        """No photo layer should pass (no occlusion possible)."""
        assert check_text_occlusion(None, {"x": 0.5, "y": 0.5, "width": 0.5, "height": 0.1}) is True


class TestContrastCheck:
    def test_high_contrast_passes(self):
        """White text (#fff) on dark background (#111) passes WCAG AA."""
        assert check_contrast_wcag_aa("#111111", "#ffffff") is True
        assert check_contrast_wcag_aa("#000000", "#ffffff") is True

    def test_low_contrast_fails(self):
        """Gray text (#888) on gray background (#999) fails WCAG AA."""
        assert check_contrast_wcag_aa("#999999", "#888888") is False

    def test_returns_true_without_colors(self):
        """Missing color info should pass (skip check)."""
        assert check_contrast_wcag_aa(None, None) is True
        assert check_contrast_wcag_aa("#ffffff", None) is True


class TestMaskIntensityCheck:
    def test_low_opacity_passes(self):
        """Mask opacity ≤ 0.65 passes."""
        assert check_mask_intensity(0.3) is True
        assert check_mask_intensity(0.65) is True

    def test_high_opacity_fails(self):
        """Mask opacity > 0.65 fails."""
        assert check_mask_intensity(0.8) is False
        assert check_mask_intensity(1.0) is False

    def test_returns_true_without_mask(self):
        """No masks should pass."""
        assert check_mask_intensity(None) is True


class TestLayerCountCheck:
    def test_within_limit_passes(self):
        """Layers ≤ maxExtraLayers + base should pass."""
        assert check_layer_count(5, max_extra_layers=4) is True  # 1 base + 4 extra = 5 max

    def test_exceeds_limit_fails(self):
        """Layers > maxExtraLayers + base should fail."""
        assert check_layer_count(7, max_extra_layers=4) is False  # 7 > 5


class TestGradientStopsCheck:
    def test_valid_stops_pass(self):
        """2-5 stops should pass."""
        stops_2 = [{"color": "#000", "opacity": 0, "position": 0},
                    {"color": "#000", "opacity": 1, "position": 1}]
        assert check_gradient_stops(stops_2) is True

        stops_5 = [{"color": "#000", "opacity": i / 5, "position": i / 5} for i in range(5)]
        assert check_gradient_stops(stops_5) is True

    def test_too_few_stops_fails(self):
        """Less than 2 stops fails."""
        stops_1 = [{"color": "#000", "opacity": 1, "position": 0}]
        assert check_gradient_stops(stops_1) is False

    def test_too_many_stops_fails(self):
        """More than 5 stops fails."""
        stops_6 = [{"color": "#000", "opacity": i / 6, "position": i / 6} for i in range(6)]
        assert check_gradient_stops(stops_6) is False

    def test_returns_true_without_stops(self):
        """No stops (no gradient) should pass."""
        assert check_gradient_stops(None) is True


class TestScoreDesignQuality:
    def test_perfect_design_scores_high(self):
        """A well-designed slide should pass all checks and score high."""
        design = {
            "photoId": "p1",
            "templateId": "cinematic_fullscreen",
            "templateParams": {},
            "layers": [
                {"type": "background", "zIndex": 0, "rect": {"x": 0, "y": 0, "width": 1, "height": 1}},
                {"type": "image", "zIndex": 1, "source": "preview", "rect": {"x": 0.05, "y": 0.05, "width": 0.9, "height": 0.7}},
                {"type": "text", "zIndex": 2, "content": "Hello", "rect": {"x": 0.05, "y": 0.85, "width": 0.9, "height": 0.08}},
                {"type": "timeline", "zIndex": 3, "label": "2024", "rect": {"x": 0.05, "y": 0.93, "width": 0.9, "height": 0.05}},
            ],
            "styleTokens": {"--kf-background-color": "#111111", "--kf-text-color": "#ffffff"},
            "renderPolicy": {"allowHtml": False, "allowJavaScript": False},
        }
        report = score_design_quality(design, max_extra_layers=4)
        assert report.total_score >= 4
        assert report.passed
        assert report.text_occlusion_pass
        assert report.layer_count_pass

    def test_low_quality_design_fails_threshold(self):
        """A badly designed slide should fail the quality threshold."""
        design = {
            "photoId": "p1",
            "templateId": "cinematic_fullscreen",
            "templateParams": {},
            "layers": [
                {"type": "image", "zIndex": 1, "source": "preview", "rect": {"x": 0, "y": 0, "width": 1, "height": 1}},
                {"type": "text", "zIndex": 2, "content": "Overlay", "rect": {"x": 0.1, "y": 0.3, "width": 0.8, "height": 0.4}},
                {"type": "mask", "zIndex": 3, "rect": {"x": 0, "y": 0, "width": 1, "height": 1},
                 "style": {"opacity": 0.9}},
                {"type": "shape", "zIndex": 4, "rect": {"x": 0, "y": 0, "width": 1, "height": 1},
                 "fill": {"type": "linearGradient", "stops": [{"color": "#000", "opacity": 0, "position": 0}]}},
            ],
            "styleTokens": {"--kf-background-color": "#aaaaaa", "--kf-text-color": "#999999"},
            "renderPolicy": {"allowHtml": False, "allowJavaScript": False},
        }
        report = score_design_quality(design, max_extra_layers=4)
        assert report.total_score < 3  # Should fail several checks
        # Text overlaps photo center, mask too opaque, gradient has 1 stop, low contrast
        assert not report.text_occlusion_pass
        assert not report.mask_intensity_pass
        assert not report.gradient_stops_pass

    def test_score_includes_all_five_checks(self):
        """Quality report must include all 5 check results."""
        design = {
            "photoId": "p1",
            "templateId": "cinematic_fullscreen",
            "templateParams": {},
            "layers": [
                {"type": "image", "zIndex": 1, "source": "preview", "rect": {"x": 0, "y": 0, "width": 1, "height": 1}},
            ],
            "styleTokens": {},
            "renderPolicy": {"allowHtml": False, "allowJavaScript": False},
        }
        report = score_design_quality(design, max_extra_layers=4)
        assert hasattr(report, 'text_occlusion_pass')
        assert hasattr(report, 'contrast_pass')
        assert hasattr(report, 'mask_intensity_pass')
        assert hasattr(report, 'layer_count_pass')
        assert hasattr(report, 'gradient_stops_pass')
