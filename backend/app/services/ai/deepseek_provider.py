"""DeepSeek API provider — calls DeepSeek chat/completions for slide design generation."""

from __future__ import annotations

import json
import re

from app.core.config import Settings


class DeepSeekProvider:
    """Calls the DeepSeek REST API with JSON mode for structured slide design output."""

    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.deepseek_base_url.rstrip("/")
        self._api_key = settings.deepseek_api_key
        self._model = settings.deepseek_model
        self._timeout = settings.ai_request_timeout_seconds
        self._client: object = None

    def _get_client(self):
        import httpx

        if self._client is None:
            self._client = httpx.Client(
                headers={"Authorization": f"Bearer {self._api_key}"},
                timeout=self._timeout,
            )
        return self._client

    def generate(self, prompt: str) -> dict | None:
        """Send a prompt to DeepSeek and return parsed JSON. Returns None on failure."""
        if not self._api_key or not self._model:
            return None

        import httpx

        payload = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
            "thinking": {"type": "disabled"},
            "stream": False,
        }
        try:
            response = self._get_client().post(
                f"{self._base_url}/chat/completions",
                json=payload,
            )
            response.raise_for_status()
        except httpx.HTTPError:
            return None

        data = response.json()
        choices = data.get("choices", [])
        if not choices:
            return None

        choice = choices[0]
        if choice.get("finish_reason") != "stop":
            return None

        content = choice.get("message", {}).get("content", "")

        # Try to extract JSON from markdown code blocks
        code_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", content, re.DOTALL)
        if code_match:
            content = code_match.group(1)

        try:
            parsed = json.loads(content)
        except (json.JSONDecodeError, TypeError):
            return None

        if not isinstance(parsed, dict):
            return None

        return parsed


def generate_slide_design_from_context(
    prompt: str,
    *,
    _provider: DeepSeekProvider | None = None,
) -> dict | None:
    """Service entry: call DeepSeek to generate a slide design from a prompt."""
    provider = _provider
    if provider is None:
        from app.core.config import get_settings
        provider = DeepSeekProvider(get_settings())
    return provider.generate(prompt)
