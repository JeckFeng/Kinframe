"""Helpers for loading shared slide design assets."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

SCHEMAS_DIR = Path(__file__).resolve().parent


def _load_json(name: str) -> dict[str, Any]:
    with (SCHEMAS_DIR / name).open(encoding="utf-8") as fh:
        return json.load(fh)


@lru_cache
def load_slide_templates() -> dict[str, Any]:
    return _load_json("slide_templates.json")


@lru_cache
def load_design_presets() -> dict[str, Any]:
    return _load_json("design_presets.json")


@lru_cache
def load_layer_primitives() -> dict[str, Any]:
    return _load_json("layer_primitives.json")

def get_template_definitions() -> list[dict[str, Any]]:
    return list(load_slide_templates().get("templates", []))


def get_template_definition(template_id: str) -> dict[str, Any] | None:
    for template in get_template_definitions():
        if template.get("id") == template_id:
            return template
    return None


def get_template_ids() -> list[str]:
    return [template["id"] for template in get_template_definitions() if "id" in template]


def get_layer_types() -> list[str]:
    primitives = load_layer_primitives().get("primitives", {})
    return [name for name in primitives.keys() if isinstance(name, str)]
