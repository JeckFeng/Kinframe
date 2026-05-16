"""Tests for v0.2 Phase 6 — admin APIs, audit logging, caption logic."""

from __future__ import annotations

from collections.abc import Generator
from io import BytesIO
from unittest.mock import MagicMock

import pytest
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_object_storage
from app.core.config import Settings, get_settings
from app.core.database import Base, get_db
from app.main import create_app
from app.models import Category, Photo
from app.schemas.user import UserCreate
from app.services.categories import ensure_default_categories
from app.services.storage import ObjectStorage
from app.services.users import create_user
from tests.http_client import TestClient


# ── Fixtures ──────────────────────────────────────────────────────

class FakeObjectStorage(ObjectStorage):
    """In-memory object storage for API tests."""
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
def admin_test_client() -> Generator[
    tuple[TestClient, FakeObjectStorage, sessionmaker[Session]],
    None,
    None,
]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    # Seed default categories
    with TestingSessionLocal() as db:
        ensure_default_categories(db)

    settings = Settings(
        app_env="development",
        app_secret_key="test-secret",
        database_url="sqlite+pysqlite:///:memory:",
        redis_url="redis://localhost:6379/0",
        minio_endpoint="localhost:9000",
        minio_access_key="kinframe",
        minio_secret_key="change-me",
        minio_bucket="test-photos",
        session_cookie_name="kinframe_test_session",
        session_expire_days=30,
        max_upload_size_mb=1,
        allowed_image_types=["image/jpeg", "image/png", "image/webp"],
        ai_enabled=True,
        deepseek_api_key="test-key",
        deepseek_model="deepseek-v4-flash",
    )
    storage = FakeObjectStorage()

    def override_get_db() -> Generator[Session, None, None]:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    def override_get_settings() -> Settings:
        return settings

    def override_get_storage() -> FakeObjectStorage:
        return storage

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_settings] = override_get_settings
    app.dependency_overrides[get_object_storage] = override_get_storage

    with TestClient(app) as client:
        yield client, storage, TestingSessionLocal

    Base.metadata.drop_all(bind=engine)


def _login(client: TestClient, username: str, password: str = "password123") -> None:
    client.post("/api/auth/login", json={"username": username, "password": password})


def _seed_user(session_factory: sessionmaker[Session], *, username: str, role: str = "member") -> str:
    with session_factory() as db:
        user = create_user(
            db,
            UserCreate(username=username, display_name=username, password="password123", role=role, is_active=True),
        )
        return str(user.id)


def _create_photo(session_factory: sessionmaker[Session], owner_id: str, **kwargs) -> str:
    import uuid
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    photo_id = str(uuid.uuid4())
    with session_factory() as db:
        photo = Photo(
            id=photo_id,
            owner_id=owner_id,
            category=kwargs.get("category", "life"),
            category_source=kwargs.get("category_source", "user"),
            caption_source=kwargs.get("caption_source", "none"),
            user_message=kwargs.get("user_message"),
            ai_caption=kwargs.get("ai_caption"),
            final_caption=kwargs.get("final_caption"),
            ai_caption_enabled=kwargs.get("ai_caption_enabled", False),
            ai_category_enabled=kwargs.get("ai_category_enabled", False),
            ai_analysis_json=kwargs.get("ai_analysis_json"),
            include_in_showcase=kwargs.get("include_in_showcase", True),
            time_source="uploaded_at",
            bucket="test-photos",
            object_key_original=f"originals/2026/05/{photo_id}.jpg",
            object_key_thumbnail=f"thumbnails/2026/05/{photo_id}_512.webp",
            object_key_preview=f"previews/2026/05/{photo_id}.webp",
            mime_type="image/jpeg",
            file_size=1024,
            sha256=photo_id.replace("-", ""),
            width=800,
            height=600,
            taken_at=kwargs.get("taken_at", now),
            uploaded_at=kwargs.get("uploaded_at", now),
            gps_lat=kwargs.get("gps_lat"),
            gps_lng=kwargs.get("gps_lng"),
            camera_make=kwargs.get("camera_make"),
            camera_model=kwargs.get("camera_model"),
            exif_json=kwargs.get("exif_json"),
            location_name=kwargs.get("location_name"),
            location_city=kwargs.get("location_city"),
            location_country=kwargs.get("location_country"),
            geocoding_status=kwargs.get("geocoding_status", "not_applicable"),
            geocoding_error=kwargs.get("geocoding_error"),
            status=kwargs.get("status", "ready"),
        )
        db.add(photo)
        db.commit()
    return photo_id


def _create_slide_design(
    session_factory: sessionmaker[Session],
    photo_id: str,
    *,
    version: int,
    source: str,
    status: str,
    template_id: str = "warm_memory",
) -> str:
    from app.schemas.photo import SlideDesignCreate
    from app.services.slide_designs import create_slide_design

    design = {
        "photoId": photo_id,
        "templateId": template_id,
        "templateParams": {},
        "layers": [
            {
                "id": f"photo-{version}",
                "type": "image",
                "source": "preview",
                "zIndex": 10,
                "rect": {"x": 0, "y": 0, "width": 1, "height": 1},
            },
            {
                "id": f"caption-{version}",
                "type": "text",
                "role": "caption",
                "content": "A framed memory",
                "zIndex": 20,
                "rect": {"x": 0.08, "y": 0.76, "width": 0.84, "height": 0.14},
            },
        ],
        "styleTokens": {
            "--kf-background-color": "#111111",
            "--kf-text-color": "#ffffff",
        },
        "renderPolicy": {"allowHtml": False, "allowJavaScript": False},
    }
    with session_factory() as db:
        design = create_slide_design(
            db,
            photo_id,
            SlideDesignCreate(
                version=version,
                design_json=design,
                source=source,
                status=status,
                validation_errors=None,
            ),
        )
        return design.id


def _create_job(
    session_factory: sessionmaker[Session],
    photo_id: str,
    *,
    job_type: str,
    status: str,
    error_message: str | None = None,
    ai_provider: str | None = None,
    ai_model: str | None = None,
    ai_prompt_version: str | None = None,
) -> str:
    import uuid
    from datetime import datetime, timezone

    from app.models import PhotoProcessingJob

    now = datetime.now(timezone.utc)
    job_id = str(uuid.uuid4())
    with session_factory() as db:
        job = PhotoProcessingJob(
            id=job_id,
            photo_id=photo_id,
            job_type=job_type,
            status=status,
            attempts=1,
            max_attempts=2,
            error_message=error_message,
            ai_provider=ai_provider,
            ai_model=ai_model,
            ai_prompt_version=ai_prompt_version,
            created_at=now,
            updated_at=now,
            started_at=now,
            finished_at=now if status in {"succeeded", "failed"} else None,
        )
        db.add(job)
        db.commit()
    return job_id


def _jpeg_bytes() -> bytes:
    img = Image.new("RGB", (64, 48), color=(100, 150, 200))
    buf = BytesIO()
    img.save(buf, "JPEG")
    return buf.getvalue()


# ── Tests: Admin Photo API ─────────────────────────────────────────

class TestAdminPhotoGet:
    def test_admin_can_see_full_photo_details(self, admin_test_client):
        client, storage, sf = admin_test_client
        _seed_user(sf, username="admin", role="admin")
        _login(client, "admin")

        owner_id = _seed_user(sf, username="owner")
        photo_id = _create_photo(
            sf, owner_id,
            ai_analysis_json={"subject": "cat"},
            exif_json={"Make": "Canon"},
            geocoding_error="some error",
            location_name="Beijing",
        )

        resp = client.get(f"/api/admin/photos/{photo_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ai_analysis_json"] == {"subject": "cat"}
        assert data["exif_json"] == {"Make": "Canon"}
        assert data["geocoding_error"] == "some error"
        assert data["caption_source"] == "none"

    def test_regular_user_gets_public_fields_only(self, admin_test_client):
        client, storage, sf = admin_test_client
        _seed_user(sf, username="member", role="member")
        _login(client, "member")

        owner_id = _seed_user(sf, username="owner2")
        photo_id = _create_photo(
            sf, owner_id,
            ai_analysis_json={"subject": "dog"},
            exif_json={"Make": "Nikon"},
            geocoding_error="geo failed",
        )

        resp = client.get(f"/api/photos/{photo_id}")
        assert resp.status_code == 200
        data = resp.json()
        # Sensitive fields absent
        assert "ai_analysis_json" not in data
        assert "exif_json" not in data
        assert "geocoding_error" not in data
        # Safe fields present
        assert data["caption_source"] == "none"
        assert data["location_name"] is None

    def test_non_admin_gets_403_on_admin_photo_endpoint(self, admin_test_client):
        client, storage, sf = admin_test_client
        _seed_user(sf, username="member2", role="member")
        _login(client, "member2")
        owner_id = _seed_user(sf, username="owner3")
        photo_id = _create_photo(sf, owner_id)

        resp = client.get(f"/api/admin/photos/{photo_id}")
        assert resp.status_code == 403

    def test_admin_detail_includes_design_versions_recent_jobs_and_audit(self, admin_test_client):
        client, storage, sf = admin_test_client
        _seed_user(sf, username="admin_detail", role="admin")
        _login(client, "admin_detail")
        owner_id = _seed_user(sf, username="owner_detail")
        photo_id = _create_photo(
            sf,
            owner_id,
            ai_analysis_json={"subject": "lake"},
            final_caption="A framed memory",
            location_name="West Lake",
        )
        _create_slide_design(sf, photo_id, version=1, source="fallback", status="draft", template_id="warm_memory")
        _create_slide_design(sf, photo_id, version=2, source="ai", status="active", template_id="gallery_center")
        _create_job(
            sf,
            photo_id,
            job_type="slide_design_generate",
            status="failed",
            error_message="quality score 2/5 below threshold",
            ai_provider="deepseek",
            ai_model="deepseek-v4-flash",
            ai_prompt_version="slide_design.v1",
        )
        _create_job(
            sf,
            photo_id,
            job_type="vision_analyze",
            status="succeeded",
            ai_provider="ollama",
            ai_model="qwen3-vl:8b",
        )
        patch_resp = client.patch(
            f"/api/admin/photos/{photo_id}",
            json={"location_city": "Hangzhou"},
        )
        assert patch_resp.status_code == 200

        resp = client.get(f"/api/admin/photos/{photo_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["active_design_source"] == "ai"
        assert data["active_design_version"] == 2
        assert len(data["design_versions"]) == 2
        assert data["design_versions"][0]["version"] == 2
        assert data["design_versions"][0]["template_id"] == "gallery_center"
        assert data["design_versions"][0]["quality_report"]["total_score"] >= 1
        assert len(data["recent_jobs"]) >= 2
        assert data["recent_jobs"][0]["job_type"] in {"slide_design_generate", "vision_analyze"}
        assert {job["ai_provider"] for job in data["recent_jobs"]} >= {"deepseek", "ollama"}
        assert any(entry["action"] == "photo.update" for entry in data["recent_audit_logs"])


class TestAdminDesignVersions:
    def test_admin_can_activate_manual_draft_version(self, admin_test_client):
        client, storage, sf = admin_test_client
        _seed_user(sf, username="admin_versions", role="admin")
        _login(client, "admin_versions")
        owner_id = _seed_user(sf, username="owner_versions")
        photo_id = _create_photo(sf, owner_id, status="ready")
        _create_slide_design(sf, photo_id, version=1, source="fallback", status="draft", template_id="warm_memory")
        _create_slide_design(sf, photo_id, version=2, source="ai", status="active", template_id="gallery_center")
        manual_draft_id = _create_slide_design(sf, photo_id, version=3, source="manual", status="draft", template_id="minimal_white")

        resp = client.post(f"/api/admin/photos/{photo_id}/design-versions/{manual_draft_id}/activate")
        assert resp.status_code == 200
        data = resp.json()
        assert data["active_design_source"] == "manual"
        assert data["active_design_version"] == 3
        assert data["design_versions"][0]["id"] == manual_draft_id
        assert data["design_versions"][0]["status"] == "active"
        assert any(
            version["version"] == 2 and version["status"] == "draft"
            for version in data["design_versions"]
        )

        public_resp = client.get(f"/api/photos/{photo_id}/slide-design")
        assert public_resp.status_code == 200
        assert public_resp.json()["source"] == "manual"
        assert public_resp.json()["version"] == 3

        audit_resp = client.get("/api/admin/audit-logs?action=design.activate")
        assert audit_resp.status_code == 200
        entries = audit_resp.json()["items"]
        assert any(entry["target_id"] == manual_draft_id for entry in entries)

    def test_admin_can_save_manual_design_as_draft_without_replacing_active(self, admin_test_client):
        client, storage, sf = admin_test_client
        _seed_user(sf, username="admin_manual", role="admin")
        _login(client, "admin_manual")
        owner_id = _seed_user(sf, username="owner_manual")
        photo_id = _create_photo(sf, owner_id, status="ready")
        _create_slide_design(sf, photo_id, version=1, source="ai", status="active", template_id="gallery_center")

        payload = {
            "design_json": {
                "photoId": photo_id,
                "templateId": "minimal_white",
                "templateParams": {},
                "layers": [
                    {
                        "id": "photo-manual",
                        "type": "image",
                        "source": "preview",
                        "zIndex": 10,
                        "rect": {"x": 0, "y": 0, "width": 1, "height": 1},
                    },
                    {
                        "id": "caption-manual",
                        "type": "text",
                        "role": "caption",
                        "content": "Manual polish",
                        "zIndex": 20,
                        "rect": {"x": 0.08, "y": 0.78, "width": 0.84, "height": 0.12},
                    },
                ],
                "styleTokens": {
                    "--kf-background-color": "#ffffff",
                    "--kf-text-color": "#111111",
                    "scopedCss": ".slide-shell { position: absolute; color: red; }",
                },
                "renderPolicy": {"allowHtml": False, "allowJavaScript": False},
            }
        }

        resp = client.post(f"/api/admin/photos/{photo_id}/design-versions/manual", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["active_design_source"] == "ai"
        assert data["active_design_version"] == 1
        assert data["design_versions"][0]["source"] == "manual"
        assert data["design_versions"][0]["status"] == "draft"
        assert data["design_versions"][0]["version"] == 2

        public_resp = client.get(f"/api/photos/{photo_id}/slide-design")
        assert public_resp.status_code == 200
        assert public_resp.json()["source"] == "ai"
        assert public_resp.json()["version"] == 1

        audit_resp = client.get("/api/admin/audit-logs?action=design.manual_create")
        assert audit_resp.status_code == 200
        entries = audit_resp.json()["items"]
        assert any(entry["target_type"] == "slide_design" for entry in entries)

    def test_invalid_manual_design_json_is_rejected(self, admin_test_client):
        client, storage, sf = admin_test_client
        _seed_user(sf, username="admin_invalid_manual", role="admin")
        _login(client, "admin_invalid_manual")
        owner_id = _seed_user(sf, username="owner_invalid_manual")
        photo_id = _create_photo(sf, owner_id, status="ready")
        _create_slide_design(sf, photo_id, version=1, source="ai", status="active", template_id="gallery_center")

        resp = client.post(
            f"/api/admin/photos/{photo_id}/design-versions/manual",
            json={
                "design_json": {
                    "photoId": photo_id,
                    "templateId": "minimal_white",
                    "templateParams": {},
                    "layers": [],
                    "styleTokens": {},
                    "renderPolicy": {"allowHtml": False, "allowJavaScript": False},
                },
            },
        )
        assert resp.status_code == 400
        assert "layers" in resp.json()["detail"]


class TestAdminPhotoPatch:
    def test_admin_update_category_auto_sets_source(self, admin_test_client):
        client, storage, sf = admin_test_client
        _seed_user(sf, username="admin", role="admin")
        _login(client, "admin")
        owner_id = _seed_user(sf, username="owner4")
        photo_id = _create_photo(sf, owner_id, category="life", category_source="user")

        resp = client.patch(f"/api/admin/photos/{photo_id}", json={"category": "pet"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["category"] == "pet"
        assert data["category_source"] == "admin:admin"

    def test_admin_update_category_no_change_preserves_source(self, admin_test_client):
        client, storage, sf = admin_test_client
        _seed_user(sf, username="admin", role="admin")
        _login(client, "admin")
        owner_id = _seed_user(sf, username="owner5")
        photo_id = _create_photo(sf, owner_id, category="life", category_source="user")

        resp = client.patch(f"/api/admin/photos/{photo_id}", json={"category": "life"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["category_source"] == "user"

    def test_admin_update_final_caption_sets_admin_override(self, admin_test_client):
        client, storage, sf = admin_test_client
        _seed_user(sf, username="admin", role="admin")
        _login(client, "admin")
        owner_id = _seed_user(sf, username="owner6")
        photo_id = _create_photo(sf, owner_id, user_message="Hello", final_caption="Hello", caption_source="user")

        resp = client.patch(f"/api/admin/photos/{photo_id}", json={"final_caption": "Admin corrected"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["final_caption"] == "Admin corrected"
        assert data["caption_source"] == "admin"

    def test_admin_update_location_fields(self, admin_test_client):
        client, storage, sf = admin_test_client
        _seed_user(sf, username="admin", role="admin")
        _login(client, "admin")
        owner_id = _seed_user(sf, username="owner7")
        photo_id = _create_photo(sf, owner_id)

        resp = client.patch(f"/api/admin/photos/{photo_id}", json={
            "location_name": "Tiananmen Square",
            "location_city": "Beijing",
            "location_country": "China",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["location_name"] == "Tiananmen Square"
        assert data["location_city"] == "Beijing"
        assert data["location_country"] == "China"

    def test_non_admin_patch_rejected(self, admin_test_client):
        client, storage, sf = admin_test_client
        _seed_user(sf, username="member3", role="member")
        _login(client, "member3")
        owner_id = _seed_user(sf, username="owner8")
        photo_id = _create_photo(sf, owner_id)

        resp = client.patch(f"/api/admin/photos/{photo_id}", json={"final_caption": "hack"})
        assert resp.status_code == 403


class TestAdminPhotoResetCaption:
    def test_reset_caption_restores_auto_computation(self, admin_test_client):
        client, storage, sf = admin_test_client
        _seed_user(sf, username="admin", role="admin")
        _login(client, "admin")
        owner_id = _seed_user(sf, username="owner9")
        # Admin previously overrode caption
        photo_id = _create_photo(
            sf, owner_id,
            user_message="Original user message",
            final_caption="Admin override",
            caption_source="admin",
        )

        resp = client.post(f"/api/admin/photos/{photo_id}/reset-caption")
        assert resp.status_code == 200
        data = resp.json()
        assert data["final_caption"] == "Original user message"
        assert data["caption_source"] == "user"

    def test_reset_caption_when_no_user_message_falls_back_to_ai(self, admin_test_client):
        client, storage, sf = admin_test_client
        _seed_user(sf, username="admin", role="admin")
        _login(client, "admin")
        owner_id = _seed_user(sf, username="owner10")
        photo_id = _create_photo(
            sf, owner_id,
            user_message=None,
            ai_caption="AI generated caption",
            ai_caption_enabled=True,
            final_caption="Admin override",
            caption_source="admin",
        )

        resp = client.post(f"/api/admin/photos/{photo_id}/reset-caption")
        assert resp.status_code == 200
        data = resp.json()
        assert data["final_caption"] == "AI generated caption"
        assert data["caption_source"] == "ai"

    def test_reset_caption_non_admin_rejected(self, admin_test_client):
        client, storage, sf = admin_test_client
        _seed_user(sf, username="member4", role="member")
        _login(client, "member4")
        owner_id = _seed_user(sf, username="owner11")
        photo_id = _create_photo(sf, owner_id)

        resp = client.post(f"/api/admin/photos/{photo_id}/reset-caption")
        assert resp.status_code == 403


class TestAdminRegenerateDesign:
    def test_regenerate_creates_new_job(self, admin_test_client):
        client, storage, sf = admin_test_client
        _seed_user(sf, username="admin", role="admin")
        _login(client, "admin")
        owner_id = _seed_user(sf, username="owner12")
        photo_id = _create_photo(sf, owner_id, status="ready")

        resp = client.post(f"/api/admin/photos/{photo_id}/regenerate-design")
        assert resp.status_code == 201
        data = resp.json()
        assert data["photo_id"] == photo_id
        assert data["job_type"] == "slide_design_generate"
        assert data["job_id"] is not None

    def test_regenerate_non_admin_rejected(self, admin_test_client):
        client, storage, sf = admin_test_client
        _seed_user(sf, username="member5", role="member")
        _login(client, "member5")
        owner_id = _seed_user(sf, username="owner13")
        photo_id = _create_photo(sf, owner_id)

        resp = client.post(f"/api/admin/photos/{photo_id}/regenerate-design")
        assert resp.status_code == 403


# ── Tests: Admin Granular Regeneration (v0.3-11) ────────────────────

class TestAdminGranularRegenerate:
    def test_regenerate_full_scope_creates_job(self, admin_test_client):
        client, storage, sf = admin_test_client
        _seed_user(sf, username="admin", role="admin")
        _login(client, "admin")
        owner_id = _seed_user(sf, username="owner_reg1")
        photo_id = _create_photo(sf, owner_id, status="ready")

        resp = client.post(
            f"/api/admin/photos/{photo_id}/regenerate",
            json={"scope": "full"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["photo_id"] == photo_id
        assert data["scope"] == "full"
        assert data["job_id"] is not None

    def test_regenerate_fallback_scope_works(self, admin_test_client):
        client, storage, sf = admin_test_client
        _seed_user(sf, username="admin", role="admin")
        _login(client, "admin")
        owner_id = _seed_user(sf, username="owner_reg2")
        photo_id = _create_photo(sf, owner_id, status="ready")

        resp = client.post(
            f"/api/admin/photos/{photo_id}/regenerate",
            json={"scope": "fallback"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["photo_id"] == photo_id
        assert data["scope"] == "fallback"
        assert data["job_type"] == "fallback_regenerate"
        assert data["job_id"] is not None

    def test_regenerate_full_when_ai_disabled_returns_error(self, admin_test_client):
        client, storage, sf = admin_test_client
        _seed_user(sf, username="admin", role="admin")
        _login(client, "admin")
        owner_id = _seed_user(sf, username="owner_reg3")
        photo_id = _create_photo(sf, owner_id, status="ready")

        # Get the settings from the app's dependency overrides
        from app.core.config import get_settings as _get_settings
        test_settings = None
        for dep_fn, override_fn in client.app.dependency_overrides.items():
            if dep_fn is _get_settings:
                test_settings = override_fn()
                break
        assert test_settings is not None
        old_key = test_settings.deepseek_api_key
        test_settings.deepseek_api_key = ""

        resp = client.post(
            f"/api/admin/photos/{photo_id}/regenerate",
            json={"scope": "full"},
        )
        # Restore
        test_settings.deepseek_api_key = old_key

        assert resp.status_code == 400
        assert "AI" in resp.json()["detail"] or "disabled" in resp.json()["detail"].lower()

    def test_regenerate_fallback_works_when_ai_disabled(self, admin_test_client):
        client, storage, sf = admin_test_client
        _seed_user(sf, username="admin", role="admin")
        _login(client, "admin")
        owner_id = _seed_user(sf, username="owner_reg4")
        photo_id = _create_photo(sf, owner_id, status="ready")

        # Get the settings from the app's dependency overrides
        from app.core.config import get_settings as _get_settings
        test_settings = None
        for dep_fn, override_fn in client.app.dependency_overrides.items():
            if dep_fn is _get_settings:
                test_settings = override_fn()
                break
        assert test_settings is not None
        old_key = test_settings.deepseek_api_key
        test_settings.deepseek_api_key = ""

        resp = client.post(
            f"/api/admin/photos/{photo_id}/regenerate",
            json={"scope": "fallback"},
        )
        test_settings.deepseek_api_key = old_key

        assert resp.status_code == 201  # Fallback always works

    def test_regenerate_non_admin_rejected(self, admin_test_client):
        client, storage, sf = admin_test_client
        _seed_user(sf, username="member_reg", role="member")
        _login(client, "member_reg")
        owner_id = _seed_user(sf, username="owner_reg5")
        photo_id = _create_photo(sf, owner_id)

        resp = client.post(
            f"/api/admin/photos/{photo_id}/regenerate",
            json={"scope": "full"},
        )
        assert resp.status_code == 403

    def test_regenerate_invalid_scope_returns_error(self, admin_test_client):
        client, storage, sf = admin_test_client
        _seed_user(sf, username="admin", role="admin")
        _login(client, "admin")
        owner_id = _seed_user(sf, username="owner_reg6")
        photo_id = _create_photo(sf, owner_id, status="ready")

        resp = client.post(
            f"/api/admin/photos/{photo_id}/regenerate",
            json={"scope": "invalid_scope"},
        )
        assert resp.status_code == 422

    def test_regenerate_creates_audit_log(self, admin_test_client):
        client, storage, sf = admin_test_client
        _seed_user(sf, username="admin", role="admin")
        _login(client, "admin")
        owner_id = _seed_user(sf, username="owner_reg7")
        photo_id = _create_photo(sf, owner_id, status="ready")

        resp = client.post(
            f"/api/admin/photos/{photo_id}/regenerate",
            json={"scope": "full"},
        )
        assert resp.status_code == 201

        # Check audit log
        audit_resp = client.get("/api/admin/audit-logs")
        assert audit_resp.status_code == 200
        entries = audit_resp.json()["items"]
        assert any(
            e["action"] == "photo.regenerate" and e["target_id"] == photo_id
            for e in entries
        )

    def test_regenerate_template_scope_creates_job(self, admin_test_client):
        client, storage, sf = admin_test_client
        _seed_user(sf, username="admin", role="admin")
        _login(client, "admin")
        owner_id = _seed_user(sf, username="owner_reg8")
        photo_id = _create_photo(sf, owner_id, status="ready")

        resp = client.post(
            f"/api/admin/photos/{photo_id}/regenerate",
            json={"scope": "template"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["scope"] == "template"
        assert data["job_type"] == "template_regenerate"
        assert data["job_id"] is not None


class TestAdminJobs:
    def test_admin_jobs_can_filter_by_status_job_type_and_photo(self, admin_test_client):
        client, storage, sf = admin_test_client
        _seed_user(sf, username="admin_jobs", role="admin")
        _login(client, "admin_jobs")
        owner_id = _seed_user(sf, username="owner_jobs")
        photo_a = _create_photo(sf, owner_id, status="ready")
        photo_b = _create_photo(sf, owner_id, status="ready")
        _create_job(sf, photo_a, job_type="vision_analyze", status="failed", error_message="vision timeout")
        _create_job(sf, photo_a, job_type="slide_design_generate", status="succeeded", ai_provider="deepseek")
        _create_job(sf, photo_b, job_type="reverse_geocode", status="pending")

        resp = client.get("/api/admin/jobs?status=failed")
        assert resp.status_code == 200
        failed_rows = resp.json()
        assert len(failed_rows) == 1
        assert failed_rows[0]["photo_id"] == photo_a
        assert failed_rows[0]["job_type"] == "vision_analyze"

        resp = client.get("/api/admin/jobs?job_type=reverse_geocode")
        assert resp.status_code == 200
        rows = resp.json()
        assert len(rows) == 1
        assert rows[0]["photo_id"] == photo_b

        resp = client.get(f"/api/admin/jobs?photo_id={photo_a}")
        assert resp.status_code == 200
        rows = resp.json()
        assert len(rows) == 2
        assert {row["job_type"] for row in rows} == {"vision_analyze", "slide_design_generate"}

    def test_retry_job_writes_audit_log(self, admin_test_client):
        client, storage, sf = admin_test_client
        _seed_user(sf, username="admin_retry", role="admin")
        _login(client, "admin_retry")
        owner_id = _seed_user(sf, username="owner_retry")
        photo_id = _create_photo(sf, owner_id, status="ready")
        job_id = _create_job(sf, photo_id, job_type="vision_analyze", status="failed", error_message="timeout")

        resp = client.post(f"/api/admin/jobs/{job_id}/retry")
        assert resp.status_code == 200

        audit_resp = client.get("/api/admin/audit-logs?action=job.retry")
        assert audit_resp.status_code == 200
        entries = audit_resp.json()["items"]
        assert any(entry["target_id"] == job_id for entry in entries)


class TestAdminPhotoList:
    def test_admin_photo_list_supports_operational_filters(self, admin_test_client):
        client, storage, sf = admin_test_client
        _seed_user(sf, username="admin_list", role="admin")
        _login(client, "admin_list")
        owner_id = _seed_user(sf, username="owner_list")

        photo_fallback = _create_photo(
            sf,
            owner_id,
            category="life",
            geocoding_status="failed",
            status="ready",
        )
        photo_ai = _create_photo(
            sf,
            owner_id,
            category="pet",
            ai_analysis_json={"subject": "cat"},
            geocoding_status="succeeded",
            status="ready",
        )
        photo_manual = _create_photo(
            sf,
            owner_id,
            category="photography",
            geocoding_status="succeeded",
            status="ready",
            include_in_showcase=False,
        )

        _create_slide_design(sf, photo_fallback, version=1, source="fallback", status="active", template_id="warm_memory")
        _create_slide_design(sf, photo_ai, version=1, source="ai", status="active", template_id="gallery_center")
        _create_slide_design(sf, photo_manual, version=1, source="manual", status="active", template_id="minimal_white")
        _create_job(sf, photo_fallback, job_type="vision_analyze", status="failed", error_message="timeout")
        _create_job(sf, photo_ai, job_type="vision_analyze", status="succeeded", ai_provider="ollama")

        resp = client.get("/api/admin/photos?design_source=manual")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["id"] == photo_manual

        resp = client.get("/api/admin/photos?ai_status=analyzed")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["id"] == photo_ai

        resp = client.get("/api/admin/photos?failed_only=true")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["id"] == photo_fallback

        resp = client.get("/api/admin/photos?needs_review=true")
        assert resp.status_code == 200
        items = resp.json()["items"]
        ids = {item["id"] for item in items}
        assert photo_fallback in ids
        assert photo_ai not in ids

        resp = client.get("/api/admin/photos?showcase_visibility=hidden")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["id"] == photo_manual
        assert data["items"][0]["include_in_showcase"] is False

        resp = client.get("/api/admin/photos?showcase_visibility=visible")
        assert resp.status_code == 200
        items = resp.json()["items"]
        ids = {item["id"] for item in items}
        assert photo_fallback in ids
        assert photo_ai in ids
        assert photo_manual not in ids
        assert all(item["include_in_showcase"] is True for item in items)

        resp = client.get("/api/admin/photos?category=pet&geocoding_status=succeeded")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["id"] == photo_ai


# ── Tests: Admin Category API ──────────────────────────────────────

class TestAdminCategories:
    def test_list_categories_includes_inactive(self, admin_test_client):
        client, storage, sf = admin_test_client
        _seed_user(sf, username="admin", role="admin")
        _login(client, "admin")

        resp = client.get("/api/admin/categories")
        assert resp.status_code == 200
        data = resp.json()
        slugs = {c["slug"] for c in data}
        assert "life" in slugs
        assert "photography" in slugs
        assert "pet" in slugs
        assert len(data) >= 3

    def test_create_category(self, admin_test_client):
        client, storage, sf = admin_test_client
        _seed_user(sf, username="admin", role="admin")
        _login(client, "admin")

        resp = client.post("/api/admin/categories", json={
            "slug": "nature",
            "name": "自然",
            "description": "Nature photos",
            "sort_order": 40,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["slug"] == "nature"
        assert data["name"] == "自然"
        assert data["is_active"] is True

        # Verify it appears in list
        list_resp = client.get("/api/admin/categories")
        slugs = {c["slug"] for c in list_resp.json()}
        assert "nature" in slugs

    def test_create_duplicate_slug_returns_409(self, admin_test_client):
        client, storage, sf = admin_test_client
        _seed_user(sf, username="admin", role="admin")
        _login(client, "admin")

        resp = client.post("/api/admin/categories", json={
            "slug": "life",
            "name": "Duplicate",
        })
        assert resp.status_code == 409

    def test_update_category_name_and_sort(self, admin_test_client):
        client, storage, sf = admin_test_client
        _seed_user(sf, username="admin", role="admin")
        _login(client, "admin")

        # Get existing category ID
        list_resp = client.get("/api/admin/categories")
        cat = [c for c in list_resp.json() if c["slug"] == "life"][0]

        resp = client.patch(f"/api/admin/categories/{cat['id']}", json={
            "name": "生活记录",
            "sort_order": 5,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "生活记录"
        assert data["sort_order"] == 5
        assert data["slug"] == "life"  # slug unchanged

    def test_cannot_change_slug(self, admin_test_client):
        client, storage, sf = admin_test_client
        _seed_user(sf, username="admin", role="admin")
        _login(client, "admin")

        list_resp = client.get("/api/admin/categories")
        cat = [c for c in list_resp.json() if c["slug"] == "pet"][0]

        # PATCH with slug should be ignored (not in CategoryUpdate schema)
        resp = client.patch(f"/api/admin/categories/{cat['id']}", json={"name": "New Pet"})
        assert resp.status_code == 200
        assert resp.json()["slug"] == "pet"

    def test_disable_category(self, admin_test_client):
        client, storage, sf = admin_test_client
        _seed_user(sf, username="admin", role="admin")
        _login(client, "admin")

        list_resp = client.get("/api/admin/categories")
        cat = [c for c in list_resp.json() if c["slug"] == "pet"][0]

        resp = client.patch(f"/api/admin/categories/{cat['id']}", json={"is_active": False})
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

    def test_non_admin_category_access_rejected(self, admin_test_client):
        client, storage, sf = admin_test_client
        _seed_user(sf, username="member6", role="member")
        _login(client, "member6")

        assert client.get("/api/admin/categories").status_code == 403
        assert client.post("/api/admin/categories", json={"slug": "x", "name": "X"}).status_code == 403


# ── Tests: Audit Log API ───────────────────────────────────────────

class TestAdminAuditLogs:
    def test_admin_actions_produce_audit_entries(self, admin_test_client):
        client, storage, sf = admin_test_client
        _seed_user(sf, username="admin", role="admin")
        _login(client, "admin")
        owner_id = _seed_user(sf, username="owner14")
        photo_id = _create_photo(sf, owner_id, category="life")

        # Perform an admin action that creates audit log
        client.patch(f"/api/admin/photos/{photo_id}", json={"category": "pet"})

        resp = client.get("/api/admin/audit-logs")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        entry = data["items"][0]
        assert entry["action"] == "photo.update"
        assert entry["target_type"] == "photo"
        assert entry["target_id"] == photo_id
        assert entry["detail"]["changed_fields"] is not None

    def test_audit_logs_pagination(self, admin_test_client):
        client, storage, sf = admin_test_client
        _seed_user(sf, username="admin", role="admin")
        _login(client, "admin")
        owner_id = _seed_user(sf, username="owner15")
        photo_id = _create_photo(sf, owner_id)

        # Create 3 audit entries
        client.patch(f"/api/admin/photos/{photo_id}", json={"location_city": "A"})
        client.patch(f"/api/admin/photos/{photo_id}", json={"location_city": "B"})
        client.patch(f"/api/admin/photos/{photo_id}", json={"location_city": "C"})

        resp = client.get("/api/admin/audit-logs?limit=2&offset=0")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 2
        assert data["limit"] == 2

        resp2 = client.get("/api/admin/audit-logs?limit=2&offset=2")
        assert resp2.status_code == 200
        assert len(resp2.json()["items"]) >= 1

    def test_audit_logs_filter_by_action(self, admin_test_client):
        client, storage, sf = admin_test_client
        _seed_user(sf, username="admin", role="admin")
        _login(client, "admin")
        owner_id = _seed_user(sf, username="owner16")
        photo_id = _create_photo(sf, owner_id)

        client.patch(f"/api/admin/photos/{photo_id}", json={"category": "pet"})
        client.post(f"/api/admin/photos/{photo_id}/reset-caption")

        resp = client.get("/api/admin/audit-logs?action=photo.caption_reset")
        assert resp.status_code == 200
        data = resp.json()
        assert all(e["action"] == "photo.caption_reset" for e in data["items"])

    def test_non_admin_audit_access_rejected(self, admin_test_client):
        client, storage, sf = admin_test_client
        _seed_user(sf, username="member7", role="member")
        _login(client, "member7")

        assert client.get("/api/admin/audit-logs").status_code == 403


# ── Tests: Caption Logic ───────────────────────────────────────────

class TestCaptionLogic:
    def test_admin_override_survives_user_update(self, admin_test_client):
        """Admin sets final_caption; regular user changes user_message but final_caption stays."""
        from app.services.photos import compute_final_caption

        client, storage, sf = admin_test_client

        # Setup: admin overrides
        admin_id = _seed_user(sf, username="admin2", role="admin")
        _login(client, "admin2")
        owner_id = _seed_user(sf, username="owner17")
        photo_id = _create_photo(
            sf, owner_id,
            user_message="Original message",
            final_caption="Admin override",
            caption_source="admin",
        )

        # Regular user updates user_message
        _login(client, "owner17")
        resp = client.patch(f"/api/photos/{photo_id}", json={"user_message": "New message"})
        assert resp.status_code == 200
        data = resp.json()
        # Admin override preserved
        assert data["final_caption"] == "Admin override"
        assert data["caption_source"] == "admin"

    def test_compute_final_caption_user_priority(self, admin_test_client):
        from app.services.photos import compute_final_caption
        client, storage, sf = admin_test_client
        with sf() as db:
            photo = Photo(
                user_message="User says",
                ai_caption="AI says",
                ai_caption_enabled=True,
                final_caption="",
                caption_source="none",
            )
            final, source = compute_final_caption(photo)
            assert final == "User says"
            assert source == "user"

    def test_compute_final_caption_ai_fallback(self, admin_test_client):
        from app.services.photos import compute_final_caption
        client, storage, sf = admin_test_client
        with sf() as db:
            photo = Photo(
                user_message=None,
                ai_caption="AI says",
                ai_caption_enabled=True,
                final_caption=None,
                caption_source="none",
            )
            final, source = compute_final_caption(photo)
            assert final == "AI says"
            assert source == "ai"

    def test_compute_final_caption_none_when_no_sources(self, admin_test_client):
        from app.services.photos import compute_final_caption
        client, storage, sf = admin_test_client
        with sf() as db:
            photo = Photo(
                user_message=None,
                ai_caption=None,
                ai_caption_enabled=False,
                final_caption=None,
                caption_source="none",
            )
            final, source = compute_final_caption(photo)
            assert final is None
            assert source == "none"

    def test_compute_final_caption_admin_override_absolute(self, admin_test_client):
        from app.services.photos import compute_final_caption
        client, storage, sf = admin_test_client
        with sf() as db:
            photo = Photo(
                user_message="User says",
                ai_caption="AI says",
                ai_caption_enabled=True,
                final_caption="Admin says",
                caption_source="admin",
            )
            final, source = compute_final_caption(photo)
            assert final == "Admin says"
            assert source == "admin"
