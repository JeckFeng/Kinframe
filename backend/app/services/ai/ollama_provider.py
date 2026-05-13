"""Ollama vision analysis provider — calls local Ollama REST API with base64 images."""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass

from app.core.config import Settings
from app.services.storage import ObjectStorage


@dataclass
class VisionAnalysisResult:
    """Normalized vision analysis output — provider-agnostic schema."""

    schema_version: str = "vision_analysis.v1"
    subject: str | None = None
    scene: str | None = None
    mood: list[str] | None = None
    dominant_colors: list[str] | None = None
    weather: str | None = None
    environment: str | None = None
    suggested_category: str | None = None
    category_confidence: float | None = None
    quality: str | None = None
    quality_notes: str | None = None


class OllamaVisionProvider:
    """Calls the Ollama REST API for vision analysis with structured JSON output."""

    def __init__(self, settings: Settings) -> None:
        self._endpoint = settings.ollama_endpoint.rstrip("/") if settings.ollama_endpoint else None
        self._model = settings.ollama_vision_model
        self._timeout = settings.ai_request_timeout_seconds
        self._client: object = None

    def _get_client(self):
        import httpx

        if self._client is None:
            self._client = httpx.Client(timeout=self._timeout)
        return self._client

    def analyze(self, image_bytes: bytes) -> VisionAnalysisResult | None:
        """Send an image to Ollama for vision analysis. Returns None on failure."""
        if not self._endpoint or not self._model:
            return None

        import httpx

        encoded = base64.b64encode(image_bytes).decode("utf-8")
        payload = {
            "model": self._model,
            "format": "json",
            "stream": False,
            "images": [encoded],
            "prompt": (
                "Analyze this photo and return a JSON object with these fields: "
                "schema_version (always 'vision_analysis.v1'), "
                "subject (what is the main subject? describe only what you see, do NOT guess identity/relationship/location names/dates/sensitive attributes), "
                "scene (describe the scene/background), "
                "mood (array of mood tags like calm, happy, warm), "
                "dominant_colors (array of hex codes like #7CB342), "
                "weather (sunny/cloudy/rainy/snowy/unknown), "
                "environment (indoor/outdoor/mixed/unknown), "
                "suggested_category (one of: life, photography, pet, or null if unsure), "
                "category_confidence (0.0 to 1.0), "
                "quality (excellent/good/fair/poor/unknown), "
                "quality_notes (brief note about focus, lighting, composition). "
                "Output ONLY valid JSON, no explanation text."
            ),
        }
        try:
            response = self._get_client().post(
                f"{self._endpoint}/api/generate",
                json=payload,
            )
            response.raise_for_status()
        except httpx.HTTPError:
            return None

        data = response.json()
        content = data.get("message", {}).get("content", "")
        try:
            parsed = json.loads(content)
        except (json.JSONDecodeError, TypeError):
            return None

        if not isinstance(parsed, dict):
            return None

        return VisionAnalysisResult(
            schema_version=parsed.get("schema_version", "vision_analysis.v1"),
            subject=parsed.get("subject"),
            scene=parsed.get("scene"),
            mood=parsed.get("mood") if isinstance(parsed.get("mood"), list) else None,
            dominant_colors=parsed.get("dominant_colors") if isinstance(parsed.get("dominant_colors"), list) else None,
            weather=parsed.get("weather"),
            environment=parsed.get("environment"),
            suggested_category=parsed.get("suggested_category"),
            category_confidence=parsed.get("category_confidence"),
            quality=parsed.get("quality"),
            quality_notes=parsed.get("quality_notes"),
        )


def analyze_preview(
    storage: ObjectStorage,
    preview_key: str,
    *,
    enabled: bool = True,
    _provider: OllamaVisionProvider | None = None,
) -> VisionAnalysisResult | None:
    """Download preview and run vision analysis. Returns None when disabled or on failure."""
    if not enabled:
        return None
    try:
        image_bytes = storage.download_bytes(preview_key)
    except Exception:
        return None
    provider = _provider
    if provider is None:
        from app.core.config import get_settings
        provider = OllamaVisionProvider(get_settings())
    return provider.analyze(image_bytes)
