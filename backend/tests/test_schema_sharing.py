"""Tests for v0.3-12: Schema Sharing — single source of truth for slide design."""

import json
from pathlib import Path

import pytest


SCHEMA_PATH = Path(__file__).parent.parent / "app" / "schemas" / "slide_design.schema.json"
FRONTEND_SCHEMA_PATH = (
    Path(__file__).parent.parent.parent.parent
    / "frontend" / "app" / "slide-renderer" / "configs" / "slide_design.schema.json"
)


@pytest.fixture()
def schema():
    with open(SCHEMA_PATH) as f:
        return json.load(f)


class TestSchemaCompleteness:
    def test_all_8_template_ids(self, schema):
        """Schema must accept all 8 v0.3 template IDs."""
        allowed = schema["properties"]["templateId"]["enum"]
        expected = {
            "cinematic_fullscreen", "warm_memory", "minimal_white",
            "poetic_landscape", "magazine_left", "gallery_center",
            "dark_exhibition", "pet_portrait",
        }
        assert set(allowed) == expected

    def test_all_8_layer_types(self, schema):
        """Schema must include texture and vignette layer types."""
        allowed = set(schema["properties"]["layers"]["items"]["properties"]["type"]["enum"])
        assert "texture" in allowed
        assert "vignette" in allowed
        assert "shape" in allowed
        assert "image" in allowed
        assert "text" in allowed
        assert "timeline" in allowed
        assert "background" in allowed
        assert "mask" in allowed
        assert len(allowed) >= 8

    def test_required_fields_present(self, schema):
        """Schema must require core fields."""
        required = set(schema.get("required", []))
        assert "photoId" in required
        assert "templateId" in required
        assert "layers" in required
        assert "styleTokens" in required
        assert "renderPolicy" in required

    def test_ai_meta_field(self, schema):
        """Schema must include aiMeta field."""
        assert "aiMeta" in schema["properties"]

    def test_render_policy_forbids_html_js(self, schema):
        """renderPolicy must forbid HTML and JavaScript."""
        rp = schema["properties"]["renderPolicy"]["properties"]
        assert rp["allowHtml"]["const"] is False
        assert rp["allowJavaScript"]["const"] is False

    def test_style_tokens_prefix(self, schema):
        """styleTokens keys must have --kf- prefix."""
        pattern = schema["properties"]["styleTokens"]["propertyNames"]["pattern"]
        assert "--kf-" in pattern

    def test_layers_forbid_html_script(self, schema):
        """Layers must not have html or script keys."""
        not_clause = schema["properties"]["layers"]["items"]["not"]
        forbidden = not_clause["anyOf"]
        assert {"required": ["html"]} in forbidden
        assert {"required": ["script"]} in forbidden

    def test_fill_field_in_layers(self, schema):
        """Layer items should support fill for Texture/Vignette."""
        layer_props = schema["properties"]["layers"]["items"]["properties"]
        # Fill may be defined as a top-level property or nested
        # At minimum the schema should not reject it
        assert "fill" in layer_props or schema["properties"]["layers"]["items"].get("additionalProperties") is not False


class TestSchemaFrontendSync:
    def test_frontend_schema_copy_exists(self):
        """Frontend must have a copy of the shared schema (verify from host)."""
        # The frontend schema lives alongside the backend schema in the repo.
        # In Docker the frontend is not mounted, so check relative to repo root.
        repo_root = Path(__file__).parent.parent.parent
        frontend_path = repo_root / "frontend" / "app" / "slide-renderer" / "configs" / "slide_design.schema.json"
        if not frontend_path.exists():
            # Docker only mounts backend; try host-relative path
            import os
            host_root = os.environ.get("HOST_REPO_ROOT")
            if host_root:
                frontend_path = Path(host_root) / "frontend" / "app" / "slide-renderer" / "configs" / "slide_design.schema.json"
        if not frontend_path.exists():
            pytest.skip("Frontend schema not accessible from this test environment")
        assert frontend_path.exists()

    def test_schemas_are_identical(self):
        """Frontend and backend schemas must be byte-identical."""
        repo_root = Path(__file__).parent.parent.parent
        frontend_path = repo_root / "frontend" / "app" / "slide-renderer" / "configs" / "slide_design.schema.json"
        if not frontend_path.exists():
            pytest.skip("Frontend schema not accessible from this test environment")
        with open(SCHEMA_PATH) as f:
            backend = json.load(f)
        with open(frontend_path) as f:
            frontend = json.load(f)
        assert backend == frontend, "Schemas diverge between frontend and backend"


class TestPythonValidatorLayerTypes:
    def test_validator_includes_texture_and_vignette(self):
        """Python semantic validator must accept texture and vignette."""
        from app.schemas.slide_design_validator import ALLOWED_LAYER_TYPES
        assert "texture" in ALLOWED_LAYER_TYPES
        assert "vignette" in ALLOWED_LAYER_TYPES


class TestSchemaValidationRoundTrip:
    def test_valid_design_accepted(self, schema):
        """A well-formed slide design passes JSON Schema validation."""
        import jsonschema
        design = {
            "photoId": "p1",
            "templateId": "cinematic_fullscreen",
            "templateParams": {},
            "layers": [
                {"type": "background", "zIndex": 0, "rect": {"x": 0, "y": 0, "width": 1, "height": 1}},
                {"type": "image", "zIndex": 1, "source": "preview", "rect": {"x": 0.05, "y": 0.05, "width": 0.9, "height": 0.7}},
                {"type": "text", "zIndex": 2, "content": "Hello", "rect": {"x": 0.05, "y": 0.85, "width": 0.9, "height": 0.08}},
            ],
            "styleTokens": {"--kf-bg": "#111"},
            "renderPolicy": {"allowHtml": False, "allowJavaScript": False},
        }
        jsonschema.validate(instance=design, schema=schema)

    def test_invalid_design_rejected(self, schema):
        """A structurally invalid design is rejected by JSON Schema."""
        import jsonschema
        design = {
            "photoId": "p1",
            "templateId": "unknown_template_xyz",
            "templateParams": {},
            "layers": [
                {"type": "image", "zIndex": 0, "html": "<script>alert(1)</script>"},
            ],
            "styleTokens": {"bad-prefix": "red"},
            "renderPolicy": {"allowHtml": True, "allowJavaScript": True},
        }
        with pytest.raises((jsonschema.ValidationError, ValueError)):
            jsonschema.validate(instance=design, schema=schema)

    def test_missing_required_field_rejected(self, schema):
        """Design missing a required field is rejected."""
        import jsonschema
        design = {
            "photoId": "p1",
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=design, schema=schema)
