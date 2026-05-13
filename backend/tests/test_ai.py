"""Tests for v0.2 AI agent workflow — Ollama + DeepSeek providers, services, and worker integration."""

from __future__ import annotations

from collections.abc import Generator
from datetime import datetime, timezone
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.core.database import Base
from app.models import Photo
from app.services.ai.ollama_provider import OllamaVisionProvider, VisionAnalysisResult, analyze_preview
from app.services.photos import PHOTO_STATUS_READY
from app.services.storage import ObjectStorage
from app.services.users import create_user
from app.schemas.user import UserCreate


# ── Test fixtures ──────────────────────────────────────────────


class FakeObjectStorage(ObjectStorage):
    """In-memory object storage for tests."""

    bucket = "test-photos"

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.content_types: dict[str, str] = {}

    def ensure_bucket(self) -> None:
        pass

    def upload_bytes(self, object_key: str, data: bytes, content_type: str) -> None:
        self.objects[object_key] = data
        self.content_types[object_key] = content_type

    def presigned_get_url(self, object_key: str, expires_seconds: int = 900) -> str:
        return f"https://storage.test/{object_key}?expires={expires_seconds}"

    def download_bytes(self, object_key: str) -> bytes:
        return self.objects[object_key]

    def delete_object(self, object_key: str) -> None:
        self.objects.pop(object_key, None)
        self.content_types.pop(object_key, None)


@pytest.fixture()
def worker_db() -> Generator[Session, None, None]:
    """In-memory SQLite session for worker-level AI tests."""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    with Session(engine) as db:
        db.execute(Base.metadata.tables["categories"].insert().values([
            {"id": "c1", "slug": "life", "name": "生活照", "description": "", "sort_order": 1, "is_active": True},
            {"id": "c2", "slug": "photography", "name": "摄影照", "description": "", "sort_order": 2, "is_active": True},
            {"id": "c3", "slug": "pet", "name": "宠物照", "description": "", "sort_order": 3, "is_active": True},
        ]))
        db.commit()
    yield Session(engine)
    Base.metadata.drop_all(bind=engine)


def _seed_user(db: Session, username: str = "member", role: str = "member") -> str:
    user = create_user(db, UserCreate(username=username, display_name=username, password="password123", role=role, is_active=True))
    return str(user.id)


def _create_ready_photo(db: Session, storage: FakeObjectStorage, owner_id: str, **kwargs) -> Photo:
    """Create a photo in ready state with storage objects."""
    import uuid

    photo_id = str(uuid.uuid4())
    original_key = f"originals/2026/05/{photo_id}.jpg"
    thumbnail_key = f"thumbnails/2026/05/{photo_id}_512.webp"
    preview_key = f"previews/2026/05/{photo_id}.webp"

    # Generate a real small JPEG for preview download tests
    img = Image.new("RGB", (64, 48), color=(100, 150, 200))
    buf = BytesIO()
    img.save(buf, "JPEG")
    fake_bytes = buf.getvalue()
    storage.upload_bytes(original_key, fake_bytes, "image/jpeg")
    storage.upload_bytes(preview_key, fake_bytes, "image/webp")

    photo = Photo(
        id=photo_id,
        owner_id=owner_id,
        category=kwargs.get("category", "life"),
        category_source=kwargs.get("category_source", "user"),
        bucket="test-photos",
        object_key_original=original_key,
        object_key_thumbnail=thumbnail_key,
        object_key_preview=preview_key,
        mime_type="image/jpeg",
        file_size=len(fake_bytes),
        sha256=f"test-{photo_id[:8]}",
        status=PHOTO_STATUS_READY,
        width=kwargs.get("width", 100),
        height=kwargs.get("height", 80),
        gps_lat=kwargs.get("gps_lat"),
        gps_lng=kwargs.get("gps_lng"),
        taken_at=kwargs.get("taken_at", datetime.now(timezone.utc)),
        uploaded_at=kwargs.get("uploaded_at", datetime.now(timezone.utc)),
        user_message=kwargs.get("user_message"),
        geocoding_status="not_applicable",
        location_name=kwargs.get("location_name"),
        location_city=kwargs.get("location_city"),
        location_country=kwargs.get("location_country"),
        exif_json=kwargs.get("exif_json"),
        ai_analysis_json=kwargs.get("ai_analysis_json"),
        ai_caption_enabled=kwargs.get("ai_caption_enabled", False),
        ai_category_enabled=kwargs.get("ai_category_enabled", False),
    )
    db.add(photo)
    db.commit()
    db.refresh(photo)
    return photo


# ── OllamaVisionProvider unit tests ────────────────────────────


class TestOllamaVisionProvider:
    def test_analyze_returns_parsed_vision_result(self):
        """Provider calls Ollama API, parses JSON into VisionAnalysisResult."""
        settings = Settings(
            ollama_endpoint="http://ollama.test:11434",
            ollama_vision_model="qwen3-vl:8b",
            ai_request_timeout_seconds=10,
        )
        provider = OllamaVisionProvider(settings)

        mock_response = {
            "message": {
                "content": (
                    '{"schema_version":"vision_analysis.v1","subject":"a cat sleeping",'
                    '"scene":"indoor living room","mood":["calm","cozy"],'
                    '"dominant_colors":["#C0A080","#404040"],"weather":"unknown",'
                    '"environment":"indoor","suggested_category":"pet",'
                    '"category_confidence":0.9,"quality":"good",'
                    '"quality_notes":"well lit, sharp focus"}'
                ),
            }
        }
        mock_client = MagicMock()
        mock_client.post.return_value.raise_for_status.return_value = None
        mock_client.post.return_value.json.return_value = mock_response
        with patch.object(provider, "_get_client", return_value=mock_client):
            result = provider.analyze(b"fake-image-bytes")

        assert isinstance(result, VisionAnalysisResult)
        assert result.subject == "a cat sleeping"
        assert result.mood == ["calm", "cozy"]
        assert result.suggested_category == "pet"
        assert result.category_confidence == 0.9
        assert result.environment == "indoor"

    def test_analyze_marks_not_json_response_as_failure(self):
        """Non-JSON Ollama responses become None."""
        settings = Settings(
            ollama_endpoint="http://ollama.test:11434",
            ollama_vision_model="qwen3-vl:8b",
        )
        provider = OllamaVisionProvider(settings)

        mock_response = {"message": {"content": "This image shows a lovely sunset over the ocean"}}
        mock_client = MagicMock()
        mock_client.post.return_value.raise_for_status.return_value = None
        mock_client.post.return_value.json.return_value = mock_response
        with patch.object(provider, "_get_client", return_value=mock_client):
            result = provider.analyze(b"fake-image-bytes")

        assert result is None

    def test_analyze_returns_none_on_http_error(self):
        """HTTP errors should return None, not crash."""
        import httpx

        settings = Settings(
            ollama_endpoint="http://ollama.test:11434",
            ollama_vision_model="qwen3-vl:8b",
        )
        provider = OllamaVisionProvider(settings)

        mock_client = MagicMock()
        mock_client.post.side_effect = httpx.ConnectError("Connection refused")
        with patch.object(provider, "_get_client", return_value=mock_client):
            result = provider.analyze(b"fake-image-bytes")

        assert result is None

    def test_analyze_includes_base64_image_in_request(self):
        """Verify the Ollama request includes base64-encoded image."""
        settings = Settings(
            ollama_endpoint="http://ollama.test:11434",
            ollama_vision_model="qwen3-vl:8b",
        )
        provider = OllamaVisionProvider(settings)
        test_bytes = b"fake-image-data-for-base64"

        mock_response = {
            "message": {
                "content": '{"schema_version":"vision_analysis.v1","subject":"test","scene":"test","mood":[],"dominant_colors":[],"weather":"unknown","environment":"unknown","suggested_category":null,"category_confidence":0,"quality":"unknown","quality_notes":""}',
            }
        }
        mock_client = MagicMock()
        mock_client.post.return_value.raise_for_status.return_value = None
        mock_client.post.return_value.json.return_value = mock_response
        with patch.object(provider, "_get_client", return_value=mock_client):
            provider.analyze(test_bytes)

        call_args = mock_client.post.call_args
        assert call_args is not None
        url = call_args[0][0]
        assert url == "http://ollama.test:11434/api/generate"
        body = call_args[1]["json"]
        assert body["model"] == "qwen3-vl:8b"
        assert body["format"] == "json"
        assert body["stream"] is False
        assert "images" in body
        import base64
        assert body["images"][0] == base64.b64encode(test_bytes).decode("utf-8")


# ── analyze_preview service test ───────────────────────────────


class TestAnalyzePreview:
    def test_returns_vision_result_from_preview_bytes(self):
        """The service layer downloads preview, calls provider, returns result."""
        settings = Settings(
            ollama_endpoint="http://ollama.test:11434",
            ollama_vision_model="qwen3-vl:8b",
        )
        storage = FakeObjectStorage()

        # Create a real preview object
        img = Image.new("RGB", (64, 48), color=(100, 150, 200))
        buf = BytesIO()
        img.save(buf, "JPEG")
        storage.upload_bytes("previews/test.jpg", buf.getvalue(), "image/webp")

        expected_result = VisionAnalysisResult(
            schema_version="vision_analysis.v1",
            subject="test subject",
            scene="test scene",
            mood=["happy"],
            dominant_colors=["#FF0000"],
            weather="sunny",
            environment="outdoor",
            suggested_category="life",
            category_confidence=0.8,
            quality="good",
            quality_notes="sharp",
        )

        mock_provider = MagicMock()
        mock_provider.analyze.return_value = expected_result

        result = analyze_preview(storage, "previews/test.jpg", _provider=mock_provider)
        assert result is expected_result
        mock_provider.analyze.assert_called_once()

    def test_returns_none_when_ai_disabled(self):
        """When AI is disabled, analyze_preview returns None without calling provider."""
        storage = FakeObjectStorage()
        mock_provider = MagicMock()

        result = analyze_preview(storage, "previews/test.jpg", enabled=False, _provider=mock_provider)
        assert result is None
        mock_provider.analyze.assert_not_called()


# ── DeepSeekProvider unit tests ──────────────────────────────────


class TestDeepSeekProvider:
    def test_generate_returns_parsed_json(self):
        """Provider calls DeepSeek API, extracts JSON from response."""
        from app.services.ai.deepseek_provider import DeepSeekProvider

        settings = Settings(
            deepseek_base_url="https://api.deepseek.com",
            deepseek_api_key="test-key",
            deepseek_model="deepseek-v4-flash",
            ai_request_timeout_seconds=10,
        )
        provider = DeepSeekProvider(settings)

        mock_response = {
            "choices": [{
                "finish_reason": "stop",
                "message": {"content": '{"test": "ok"}'},
            }],
        }
        mock_client = MagicMock()
        mock_client.post.return_value.raise_for_status.return_value = None
        mock_client.post.return_value.json.return_value = mock_response
        with patch.object(provider, "_get_client", return_value=mock_client):
            result = provider.generate("test prompt")

        assert result == {"test": "ok"}

    def test_generate_returns_none_on_non_stop_finish(self):
        """If finish_reason != 'stop', return None."""
        from app.services.ai.deepseek_provider import DeepSeekProvider

        settings = Settings(
            deepseek_base_url="https://api.deepseek.com",
            deepseek_api_key="test-key",
            deepseek_model="deepseek-v4-flash",
        )
        provider = DeepSeekProvider(settings)

        mock_response = {
            "choices": [{
                "finish_reason": "length",
                "message": {"content": '{"incomplete": true}'},
            }],
        }
        mock_client = MagicMock()
        mock_client.post.return_value.raise_for_status.return_value = None
        mock_client.post.return_value.json.return_value = mock_response
        with patch.object(provider, "_get_client", return_value=mock_client):
            result = provider.generate("test prompt")

        assert result is None

    def test_generate_returns_none_on_invalid_json(self):
        """Non-JSON content returns None."""
        from app.services.ai.deepseek_provider import DeepSeekProvider

        settings = Settings(
            deepseek_base_url="https://api.deepseek.com",
            deepseek_api_key="test-key",
            deepseek_model="deepseek-v4-flash",
        )
        provider = DeepSeekProvider(settings)

        mock_response = {
            "choices": [{
                "finish_reason": "stop",
                "message": {"content": "not json at all"},
            }],
        }
        mock_client = MagicMock()
        mock_client.post.return_value.raise_for_status.return_value = None
        mock_client.post.return_value.json.return_value = mock_response
        with patch.object(provider, "_get_client", return_value=mock_client):
            result = provider.generate("test prompt")

        assert result is None

    def test_generate_returns_none_on_http_error(self):
        """HTTP errors return None."""
        import httpx
        from app.services.ai.deepseek_provider import DeepSeekProvider

        settings = Settings(
            deepseek_base_url="https://api.deepseek.com",
            deepseek_api_key="test-key",
            deepseek_model="deepseek-v4-flash",
        )
        provider = DeepSeekProvider(settings)

        mock_client = MagicMock()
        mock_client.post.side_effect = httpx.ConnectError("Connection refused")
        with patch.object(provider, "_get_client", return_value=mock_client):
            result = provider.generate("test prompt")

        assert result is None

    def test_generate_uses_json_mode_and_disables_thinking(self):
        """Verify JSON mode, temperature, thinking disabled."""
        from app.services.ai.deepseek_provider import DeepSeekProvider

        settings = Settings(
            deepseek_base_url="https://api.deepseek.com",
            deepseek_api_key="test-key",
            deepseek_model="deepseek-v4-flash",
        )
        provider = DeepSeekProvider(settings)

        mock_response = {
            "choices": [{
                "finish_reason": "stop",
                "message": {"content": '{"x": 1}'},
            }],
        }
        mock_client = MagicMock()
        mock_client.post.return_value.raise_for_status.return_value = None
        mock_client.post.return_value.json.return_value = mock_response
        with patch.object(provider, "_get_client", return_value=mock_client):
            provider.generate("test prompt")

        call_args = mock_client.post.call_args
        url = call_args[0][0]
        assert url == "https://api.deepseek.com/chat/completions"
        body = call_args[1]["json"]
        assert body["model"] == "deepseek-v4-flash"
        assert body["response_format"] == {"type": "json_object"}
        assert body["temperature"] == 0.2
        assert body["thinking"] == {"type": "disabled"}
        assert body["stream"] is False

    def test_extracts_json_from_markdown_code_block(self):
        """JSON wrapped in ```json ... ``` should be extractable."""
        from app.services.ai.deepseek_provider import DeepSeekProvider

        settings = Settings(
            deepseek_base_url="https://api.deepseek.com",
            deepseek_api_key="test-key",
            deepseek_model="deepseek-v4-flash",
        )
        provider = DeepSeekProvider(settings)

        content = '```json\n{"slide": "design"}\n```'
        mock_response = {
            "choices": [{
                "finish_reason": "stop",
                "message": {"content": content},
            }],
        }
        mock_client = MagicMock()
        mock_client.post.return_value.raise_for_status.return_value = None
        mock_client.post.return_value.json.return_value = mock_response
        with patch.object(provider, "_get_client", return_value=mock_client):
            result = provider.generate("test prompt")

        assert result == {"slide": "design"}


# ── Slide Design Prompt Builder tests ─────────────────────────────


class TestSlideDesignPromptBuilder:
    def test_includes_all_template_ids(self):
        """Prompt must list all 3 template IDs for DeepSeek to choose from."""
        from app.services.ai.slide_design_prompt import build_slide_design_prompt

        prompt = build_slide_design_prompt(
            photo_id="p1",
            photo_category="life",
            user_message=None,
            taken_at_str="2024-03-15T10:30:00Z",
            location_summary=None,
            vision_result=None,
            prev_errors=None,
        )
        assert "cinematic_fullscreen" in prompt
        assert "warm_memory" in prompt
        assert "minimal_white" in prompt
        assert "p1" in prompt

    def test_includes_layer_types_and_constraints(self):
        """Prompt must describe available layer types and their constraints."""
        from app.services.ai.slide_design_prompt import build_slide_design_prompt

        prompt = build_slide_design_prompt(
            photo_id="p1",
            photo_category="life",
            user_message=None,
            taken_at_str="2024-03-15T10:30:00Z",
            location_summary=None,
            vision_result=None,
            prev_errors=None,
        )
        for lt in ("shape", "image", "text", "timeline", "background", "mask"):
            assert lt in prompt
        assert "zIndex" in prompt
        assert "--kf-" in prompt

    def test_user_message_takes_priority_over_ai(self):
        """When user_message exists, prompt must instruct NOT to rewrite caption."""
        from app.services.ai.slide_design_prompt import build_slide_design_prompt

        prompt = build_slide_design_prompt(
            photo_id="p1",
            photo_category="life",
            user_message="My special caption",
            taken_at_str="2024-03-15T10:30:00Z",
            location_summary=None,
            vision_result=None,
            prev_errors=None,
        )
        assert "My special caption" in prompt
        assert "do not rewrite" in prompt.lower() or "do not change" in prompt.lower() or "do not replace" in prompt.lower()

    def test_includes_vision_result_when_available(self):
        """Vision analysis output must be included in the prompt context."""
        from app.services.ai.slide_design_prompt import build_slide_design_prompt
        from app.services.ai.ollama_provider import VisionAnalysisResult

        vision = VisionAnalysisResult(
            subject="a cat on a sofa",
            scene="indoor living room",
            mood=["calm"],
            dominant_colors=["#C0A080", "#404040"],
            weather="unknown",
            environment="indoor",
            suggested_category="pet",
            category_confidence=0.9,
            quality="good",
            quality_notes="sharp focus",
        )
        prompt = build_slide_design_prompt(
            photo_id="p1",
            photo_category="life",
            user_message=None,
            taken_at_str="2024-03-15T10:30:00Z",
            location_summary=None,
            vision_result=vision,
            prev_errors=None,
        )
        assert "cat" in prompt
        assert "calm" in prompt.lower()

    def test_vision_missing_degrades_prompt(self):
        """When vision_result is None, prompt must say vision analysis is unavailable."""
        from app.services.ai.slide_design_prompt import build_slide_design_prompt

        prompt = build_slide_design_prompt(
            photo_id="p1",
            photo_category="life",
            user_message=None,
            taken_at_str="2024-03-15T10:30:00Z",
            location_summary=None,
            vision_result=None,
            prev_errors=None,
        )
        assert "no visual analysis" in prompt.lower() or "not available" in prompt.lower()

    def test_includes_previous_errors_for_correction_retry(self):
        """On retry, prompt should include previous validation errors."""
        from app.services.ai.slide_design_prompt import build_slide_design_prompt

        prompt = build_slide_design_prompt(
            photo_id="p1",
            photo_category="life",
            user_message=None,
            taken_at_str="2024-03-15T10:30:00Z",
            location_summary=None,
            vision_result=None,
            prev_errors=["layer 0 has unsupported type: video", "layers must include at least one image layer"],
        )
        assert "unsupported type" in prompt
        assert "image layer" in prompt.lower()

    def test_includes_location_when_available(self):
        """Location summary should appear when available."""
        from app.services.ai.slide_design_prompt import build_slide_design_prompt

        prompt = build_slide_design_prompt(
            photo_id="p1",
            photo_category="life",
            user_message=None,
            taken_at_str="2024-03-15T10:30:00Z",
            location_summary="Beijing, China",
            vision_result=None,
            prev_errors=None,
        )
        assert "Beijing" in prompt


# ── Worker integration tests ──────────────────────────────────────


class TestVisionAnalyzeJob:
    def test_process_vision_analyze_job_success(self, worker_db):
        """Full vision_analyze job: downloads preview, calls Ollama, writes ai_analysis_json."""
        from app.services.ai.ollama_provider import VisionAnalysisResult
        from app.services.photo_jobs import (
            PHOTO_JOB_STATUS_SUCCEEDED,
            create_vision_analyze_job,
            process_vision_analyze_job,
        )

        storage = FakeObjectStorage()
        db = worker_db
        owner_id = _seed_user(db)
        photo = _create_ready_photo(db, storage, owner_id)

        # Create vision_analyze job
        job = create_vision_analyze_job(db, photo.id, max_attempts=2)
        assert job.job_type == "vision_analyze"
        assert job.status == "pending"

        # Mock provider
        expected_result = VisionAnalysisResult(
            subject="test subject",
            scene="test scene",
            mood=["happy"],
            dominant_colors=["#FF0000"],
            weather="sunny",
            environment="outdoor",
            suggested_category="life",
            category_confidence=0.8,
            quality="good",
            quality_notes="sharp",
        )
        mock_provider = MagicMock()
        mock_provider.analyze.return_value = expected_result

        # Process
        assert process_vision_analyze_job(db, job, photo, storage, _provider=mock_provider)

        # Verify
        db.refresh(job)
        db.refresh(photo)
        assert job.status == PHOTO_JOB_STATUS_SUCCEEDED
        assert photo.ai_analysis_json is not None
        assert photo.ai_analysis_json.get("subject") == "test subject"
        assert photo.ai_analysis_json.get("mood") == ["happy"]

    def test_process_vision_analyze_job_no_preview_marks_failed(self, worker_db):
        """Photo without preview object_key should fail gracefully."""
        from app.services.photo_jobs import create_vision_analyze_job, process_vision_analyze_job

        storage = FakeObjectStorage()
        db = worker_db
        owner_id = _seed_user(db)
        photo = _create_ready_photo(db, storage, owner_id)
        photo.object_key_preview = None
        db.commit()

        job = create_vision_analyze_job(db, photo.id, max_attempts=1)
        assert process_vision_analyze_job(db, job, photo, storage, _provider=MagicMock())

        db.refresh(photo)
        assert photo.status == "ready"  # unchanged!
        assert photo.ai_analysis_json is None

    def test_process_vision_analyze_job_ollama_failure_marks_failed(self, worker_db):
        """Ollama failure marks job failed, photo stays ready."""
        from app.services.photo_jobs import create_vision_analyze_job, process_vision_analyze_job

        storage = FakeObjectStorage()
        db = worker_db
        owner_id = _seed_user(db)
        photo = _create_ready_photo(db, storage, owner_id)

        job = create_vision_analyze_job(db, photo.id, max_attempts=1)
        mock_provider = MagicMock()
        mock_provider.analyze.return_value = None

        assert process_vision_analyze_job(db, job, photo, storage, _provider=mock_provider)
        db.refresh(photo)
        assert photo.status == "ready"  # invariant
        assert photo.ai_analysis_json is None


class TestSlideDesignGenerateJob:
    def test_process_slide_design_generate_job_success(self, worker_db):
        """Full slide_design_generate: builds prompt, calls DeepSeek, validates, atomically swaps active."""
        from app.services.photo_jobs import (
            PHOTO_JOB_STATUS_SUCCEEDED,
            create_slide_design_generate_job,
            process_slide_design_generate_job,
        )

        storage = FakeObjectStorage()
        db = worker_db
        owner_id = _seed_user(db)
        photo = _create_ready_photo(db, storage, owner_id, user_message="Hello world")

        # Create fallback design (simulating ingest)
        from app.services.slide_designs import create_slide_design
        from app.schemas.photo import SlideDesignCreate
        fallback_design = {
            "photoId": photo.id,
            "templateId": "cinematic_fullscreen",
            "templateParams": {},
            "layers": [{
                "type": "image", "zIndex": 1,
                "rect": {"x": 0, "y": 0, "width": 1, "height": 1},
                "source": "preview",
            }],
            "styleTokens": {"--kf-background-color": "#111111"},
            "renderPolicy": {"allowHtml": False, "allowJavaScript": False},
        }
        create_slide_design(db, photo.id, SlideDesignCreate(
            version=1, design_json=fallback_design, source="fallback", status="active",
        ))

        job = create_slide_design_generate_job(db, photo.id, max_attempts=2, provider_name="deepseek")
        assert job.job_type == "slide_design_generate"

        # Mock DeepSeek response: valid AI design
        ai_design = {
            "photoId": photo.id,
            "templateId": "warm_memory",
            "templateParams": {},
            "layers": [
                {"type": "background", "zIndex": 0, "rect": {"x": 0, "y": 0, "width": 1, "height": 1}},
                {"type": "image", "zIndex": 1, "source": "preview", "rect": {"x": 0.06, "y": 0.08, "width": 0.88, "height": 0.74}},
                {"type": "text", "zIndex": 20, "content": "Hello world", "rect": {"x": 0.08, "y": 0.78, "width": 0.72, "height": 0.1}},
                {"type": "timeline", "zIndex": 30, "label": "2024-03-15", "rect": {"x": 0.08, "y": 0.91, "width": 0.84, "height": 0.05}},
            ],
            "styleTokens": {"--kf-background-color": "#f7f5ef", "--kf-text-color": "#171717"},
            "renderPolicy": {"allowHtml": False, "allowJavaScript": False},
            "aiMeta": {"provider": "deepseek", "model": "deepseek-v4-flash", "promptVersion": "slide_design.v1"},
        }
        mock_provider = MagicMock()
        mock_provider.generate.return_value = ai_design

        assert process_slide_design_generate_job(db, job, photo, _provider=mock_provider)
        db.refresh(job)
        assert job.status == PHOTO_JOB_STATUS_SUCCEEDED

        # Verify atomic swap: old fallback now draft, AI active
        from app.services.slide_designs import get_latest_active_slide_design
        active = get_latest_active_slide_design(db, photo.id)
        assert active is not None
        assert active.source == "ai"
        assert active.version == 2

    def test_process_slide_design_generate_invalid_json_fails(self, worker_db):
        """DeepSeek returning invalid JSON should mark job failed, keep fallback active."""
        from app.services.photo_jobs import create_slide_design_generate_job, process_slide_design_generate_job

        storage = FakeObjectStorage()
        db = worker_db
        owner_id = _seed_user(db)
        photo = _create_ready_photo(db, storage, owner_id)

        # Create fallback
        from app.services.slide_designs import create_slide_design
        from app.schemas.photo import SlideDesignCreate
        fallback = {
            "photoId": photo.id, "templateId": "cinematic_fullscreen",
            "templateParams": {},
            "layers": [{"type": "image", "zIndex": 1, "source": "preview", "rect": {"x": 0, "y": 0, "width": 1, "height": 1}}],
            "styleTokens": {}, "renderPolicy": {"allowHtml": False, "allowJavaScript": False},
        }
        create_slide_design(db, photo.id, SlideDesignCreate(version=1, design_json=fallback, source="fallback", status="active"))

        job = create_slide_design_generate_job(db, photo.id, max_attempts=1, provider_name="deepseek")

        # Mock DeepSeek returning garbage
        mock_provider = MagicMock()
        mock_provider.generate.return_value = {"templateId": "cinematic_fullscreen", "layers": []}  # no image layer → validation fails

        assert process_slide_design_generate_job(db, job, photo, _provider=mock_provider)
        db.refresh(photo)
        assert photo.status == "ready"  # invariant

        # Fallback still active
        from app.services.slide_designs import get_latest_active_slide_design
        active = get_latest_active_slide_design(db, photo.id)
        assert active is not None
        assert active.source == "fallback"

    def test_manual_design_not_overwritten_by_ai(self, worker_db):
        """When active design is manual, AI should not replace it."""
        from app.services.photo_jobs import create_slide_design_generate_job, process_slide_design_generate_job

        storage = FakeObjectStorage()
        db = worker_db
        owner_id = _seed_user(db)
        photo = _create_ready_photo(db, storage, owner_id)

        from app.services.slide_designs import create_slide_design
        from app.schemas.photo import SlideDesignCreate
        manual_design = {
            "photoId": photo.id, "templateId": "minimal_white",
            "templateParams": {},
            "layers": [{"type": "image", "zIndex": 1, "source": "preview", "rect": {"x": 0, "y": 0, "width": 1, "height": 1}}],
            "styleTokens": {}, "renderPolicy": {"allowHtml": False, "allowJavaScript": False},
        }
        create_slide_design(db, photo.id, SlideDesignCreate(version=1, design_json=manual_design, source="manual", status="active"))

        job = create_slide_design_generate_job(db, photo.id, max_attempts=1, provider_name="deepseek")
        mock_provider = MagicMock()
        mock_provider.generate.return_value = {
            "photoId": photo.id, "templateId": "cinematic_fullscreen",
            "templateParams": {},
            "layers": [{"type": "image", "zIndex": 1, "source": "preview", "rect": {"x": 0, "y": 0, "width": 1, "height": 1}}],
            "styleTokens": {}, "renderPolicy": {"allowHtml": False, "allowJavaScript": False},
        }

        process_slide_design_generate_job(db, job, photo, _provider=mock_provider)
        db.refresh(job)
        # Should have stopped early — manual > AI
        from app.services.slide_designs import get_latest_active_slide_design
        active = get_latest_active_slide_design(db, photo.id)
        assert active is not None
        assert active.source == "manual"


class TestDuplicateJobProtection:
    def test_create_vision_analyze_job_skips_when_pending_exists(self, worker_db):
        """Second enqueue of same type should not create duplicate when pending/running exists."""
        storage = FakeObjectStorage()
        db = worker_db
        owner_id = _seed_user(db)
        photo = _create_ready_photo(db, storage, owner_id)

        from app.services.photo_jobs import create_vision_analyze_job
        job1 = create_vision_analyze_job(db, photo.id, max_attempts=2)
        job2 = create_vision_analyze_job(db, photo.id, max_attempts=2)

        # Second call should return the same job, not create a new one
        assert job2.id == job1.id
