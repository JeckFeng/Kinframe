"""Tests for v0.2 Phase 6 — admin APIs, audit logging, caption logic."""

from __future__ import annotations

from collections.abc import Generator
from io import BytesIO
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
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
        deepseek_api_key="test-key",
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
            include_in_showcase=True,
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
