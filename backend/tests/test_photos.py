"""Tests for v0 photo upload, storage, metadata, and permissions."""

from collections.abc import Generator
from datetime import datetime
from io import BytesIO

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
from app.schemas.user import UserCreate
from app.services.storage import ObjectStorage
from app.services.users import create_user


class FakeObjectStorage(ObjectStorage):
    """In-memory object storage for API tests."""

    bucket = "test-photos"

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.content_types: dict[str, str] = {}
        self.ensure_bucket_called = False

    def ensure_bucket(self) -> None:
        self.ensure_bucket_called = True

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
def client_storage_and_session_factory() -> Generator[
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


def image_bytes(fmt: str = "JPEG", size: tuple[int, int] = (12, 8)) -> bytes:
    image = Image.new("RGB", size, color=(80, 120, 180))
    output = BytesIO()
    image.save(output, format=fmt)
    return output.getvalue()


def oriented_jpeg_bytes() -> bytes:
    image = Image.new("RGB", (40, 20), color=(180, 120, 80))
    exif = Image.Exif()
    exif[274] = 6
    output = BytesIO()
    image.save(output, format="JPEG", exif=exif)
    return output.getvalue()


def seed_user(
    session_factory: sessionmaker[Session],
    *,
    username: str,
    password: str = "password123",
    role: str = "member",
) -> None:
    with session_factory() as db:
        create_user(
            db,
            UserCreate(
                username=username,
                display_name=username.title(),
                password=password,
                role=role,  # type: ignore[arg-type]
                is_active=True,
            ),
        )


def login(client: TestClient, username: str, password: str = "password123") -> None:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200


def upload_test_photo(client: TestClient, filename: str = "photo.jpg") -> dict:
    response = client.post(
        "/api/photos/upload",
        data={"category": "life", "user_message": "A quiet morning"},
        files={"file": (filename, image_bytes(), "image/jpeg")},
    )
    assert response.status_code == 201
    return response.json()


def process_one_photo_job(session_factory: sessionmaker[Session], storage: FakeObjectStorage) -> None:
    from app.services.photo_jobs import process_next_photo_job

    with session_factory() as db:
        assert process_next_photo_job(db, storage) is True


def valid_slide_design_json(photo_id: str, template_id: str = "warm_memory") -> dict:
    return {
        "photoId": photo_id,
        "templateId": template_id,
        "templateParams": {},
        "layers": [
            {
                "id": "photo",
                "type": "image",
                "source": "preview",
                "zIndex": 10,
                "rect": {"x": 0, "y": 0, "width": 1, "height": 1},
            }
        ],
        "styleTokens": {"--kf-accent-color": "#8a9a5b"},
        "renderPolicy": {"allowHtml": False, "allowJavaScript": False},
    }


def test_upload_photo_stores_objects_and_metadata(client_storage_and_session_factory) -> None:
    client, storage, session_factory = client_storage_and_session_factory
    seed_user(session_factory, username="member")
    login(client, "member")

    payload = upload_test_photo(client)

    assert payload["category"] == "life"
    assert payload["user_message"] == "A quiet morning"
    assert payload["final_caption"] == "A quiet morning"
    assert payload["status"] == "processing"
    assert payload["processing_message"] == "Photo uploaded and queued for processing"
    assert payload["ai_caption"] is None
    assert payload["ai_category_suggestion"] is None
    assert payload["ai_caption_enabled"] is False
    assert payload["ai_category_enabled"] is False
    assert payload["include_in_showcase"] is True
    assert payload["time_source"] == "uploaded_at"
    assert payload["width"] is None
    assert payload["height"] is None
    assert payload["mime_type"] == "image/jpeg"
    assert payload["bucket"] == "test-photos"
    assert payload["object_key_original"].startswith("originals/")
    assert payload["object_key_thumbnail"].startswith("thumbnails/")
    assert payload["object_key_preview"].startswith("previews/")
    assert storage.ensure_bucket_called is True
    assert payload["object_key_original"] in storage.objects
    assert payload["object_key_thumbnail"] not in storage.objects
    assert payload["object_key_preview"] not in storage.objects

    status_response = client.get(f"/api/photos/{payload['id']}/processing-status")
    assert status_response.status_code == 200
    assert status_response.json() == {
        "photo_id": payload["id"],
        "photo_status": "processing",
        "job_type": "photo_ingest",
        "job_status": "pending",
        "attempts": 0,
        "max_attempts": 3,
        "error_message": None,
        "slide_design_status": None,
        "slide_design_source": None,
        "ai_provider": None,
        "ai_model": None,
        "geocoding_status": "not_applicable",
    }


def test_upload_photo_accepts_ai_flags_and_showcase_visibility(client_storage_and_session_factory) -> None:
    client, _storage, session_factory = client_storage_and_session_factory
    seed_user(session_factory, username="member")
    login(client, "member")

    response = client.post(
        "/api/photos/upload",
        data={
            "category": "photography",
            "user_message": "Let AI help",
            "ai_caption_enabled": "true",
            "ai_category_enabled": "true",
            "include_in_showcase": "false",
        },
        files={"file": ("photo.jpg", image_bytes(), "image/jpeg")},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["category"] == "photography"
    assert payload["ai_caption_enabled"] is True
    assert payload["ai_category_enabled"] is True
    assert payload["include_in_showcase"] is False
    assert payload["time_source"] == "uploaded_at"


def test_default_categories_expose_prd_slugs(client_storage_and_session_factory) -> None:
    client, _storage, session_factory = client_storage_and_session_factory
    seed_user(session_factory, username="member")
    login(client, "member")

    response = client.get("/api/photos/categories")

    assert response.status_code == 200
    payload = response.json()
    assert [category["slug"] for category in payload] == ["life", "photography", "pet"]
    assert payload == [
        {
            "id": payload[0]["id"],
            "slug": "life",
            "name": "生活照",
            "description": "家庭日常、聚会和普通生活记录",
            "legacy_slug": None,
            "sort_order": 10,
            "is_active": True,
        },
        {
            "id": payload[1]["id"],
            "slug": "photography",
            "name": "摄影照",
            "description": "更偏摄影作品、旅行风景和构图记录",
            "legacy_slug": "travel",
            "sort_order": 20,
            "is_active": True,
        },
        {
            "id": payload[2]["id"],
            "slug": "pet",
            "name": "宠物照",
            "description": "家庭宠物和动物陪伴记录",
            "legacy_slug": None,
            "sort_order": 30,
            "is_active": True,
        },
    ]
    assert all(category["id"] for category in payload)


def test_photography_slug_filters_legacy_travel_photos(client_storage_and_session_factory) -> None:
    client, _storage, session_factory = client_storage_and_session_factory
    seed_user(session_factory, username="member")
    login(client, "member")
    legacy_photo = client.post(
        "/api/photos/upload",
        data={"category": "travel", "user_message": "Legacy travel"},
        files={"file": ("legacy.jpg", image_bytes(size=(12, 8)), "image/jpeg")},
    ).json()
    prd_photo = client.post(
        "/api/photos/upload",
        data={"category": "photography", "user_message": "PRD photography"},
        files={"file": ("prd.jpg", image_bytes(size=(13, 9)), "image/jpeg")},
    ).json()

    response = client.get("/api/photos?category=photography")

    assert response.status_code == 200
    ids = {photo["id"] for photo in response.json()}
    assert ids == {legacy_photo["id"], prd_photo["id"]}


def test_latest_active_slide_design_is_returned_for_photo(client_storage_and_session_factory) -> None:
    client, _storage, session_factory = client_storage_and_session_factory
    seed_user(session_factory, username="member")
    login(client, "member")
    photo = upload_test_photo(client)

    first = client.post(
        f"/api/photos/{photo['id']}/slide-designs",
        json={
            "version": 1,
            "source": "fallback",
            "status": "active",
            "design_json": valid_slide_design_json(photo["id"], "warm_memory"),
        },
    )
    draft = client.post(
        f"/api/photos/{photo['id']}/slide-designs",
        json={
            "version": 2,
            "source": "ai",
            "status": "draft",
            "design_json": valid_slide_design_json(photo["id"], "minimal_white"),
            "validation_errors": ["missing main image layer"],
        },
    )
    latest = client.post(
        f"/api/photos/{photo['id']}/slide-designs",
        json={
            "version": 3,
            "source": "fallback",
            "status": "active",
            "design_json": valid_slide_design_json(photo["id"], "minimal_white"),
        },
    )
    response = client.get(f"/api/photos/{photo['id']}/slide-design")

    assert first.status_code == 201
    assert draft.status_code == 201
    assert latest.status_code == 201
    assert response.status_code == 200
    payload = response.json()
    assert payload["photo_id"] == photo["id"]
    assert payload["version"] == 3
    assert payload["source"] == "fallback"
    assert payload["status"] == "active"
    assert payload["design_json"] == valid_slide_design_json(photo["id"], "minimal_white")
    assert payload["validation_errors"] is None


def test_slide_design_rejects_invalid_schema(client_storage_and_session_factory) -> None:
    client, _storage, session_factory = client_storage_and_session_factory
    seed_user(session_factory, username="member")
    login(client, "member")
    photo = upload_test_photo(client)

    response = client.post(
        f"/api/photos/{photo['id']}/slide-designs",
        json={
            "version": 1,
            "source": "fallback",
            "status": "active",
            "design_json": {
                "photoId": photo["id"],
                "templateId": "warm_memory",
                "templateParams": {},
                "layers": [
                    {
                        "id": "photo",
                        "type": "image",
                        "zIndex": 101,
                        "rect": {"x": 1.2, "y": 0, "width": 0.8, "height": 0.5},
                    }
                ],
                "styleTokens": {},
                "renderPolicy": {"allowHtml": False, "allowJavaScript": False},
            },
        },
    )

    assert response.status_code == 422


def test_upload_without_exif_uses_safe_fallback(client_storage_and_session_factory) -> None:
    client, _storage, session_factory = client_storage_and_session_factory
    seed_user(session_factory, username="member")
    login(client, "member")

    payload = upload_test_photo(client)

    assert datetime.fromisoformat(payload["taken_at"].replace("Z", "+00:00"))
    assert payload["camera_make"] is None
    assert payload["camera_model"] is None
    assert payload["gps_lat"] is None
    assert payload["gps_lng"] is None


def test_worker_success_processes_pending_photo(client_storage_and_session_factory) -> None:
    from app.services.photo_jobs import process_next_photo_job

    client, storage, session_factory = client_storage_and_session_factory
    seed_user(session_factory, username="member")
    login(client, "member")
    payload = upload_test_photo(client)

    with session_factory() as db:
        assert process_next_photo_job(db, storage) is True

    status_response = client.get(f"/api/photos/{payload['id']}/processing-status")
    detail_response = client.get(f"/api/photos/{payload['id']}")

    assert status_response.status_code == 200
    assert status_response.json()["photo_status"] == "ready"
    assert status_response.json()["job_status"] == "succeeded"
    assert status_response.json()["attempts"] == 1
    assert detail_response.status_code == 200
    assert detail_response.json()["width"] == 12
    assert detail_response.json()["height"] == 8
    assert payload["object_key_thumbnail"] in storage.objects
    assert payload["object_key_preview"] in storage.objects
    assert storage.content_types[payload["object_key_thumbnail"]] == "image/webp"
    assert storage.content_types[payload["object_key_preview"]] == "image/webp"

    preview_url = client.get(f"/api/photos/{payload['id']}/preview-url")
    assert preview_url.status_code == 200
    assert payload["object_key_preview"] in preview_url.json()["url"]


def test_worker_generates_fallback_slide_design_for_ready_photo(
    client_storage_and_session_factory,
) -> None:
    from app.services.photo_jobs import process_next_photo_job

    client, storage, session_factory = client_storage_and_session_factory
    seed_user(session_factory, username="member")
    login(client, "member")
    payload = upload_test_photo(client)

    with session_factory() as db:
        assert process_next_photo_job(db, storage) is True

    response = client.get(f"/api/photos/{payload['id']}/slide-design")

    assert response.status_code == 200
    design = response.json()
    assert design["photo_id"] == payload["id"]
    assert design["version"] == 1
    assert design["source"] == "fallback"
    assert design["status"] == "active"
    design_json = design["design_json"]
    assert design_json["photoId"] == payload["id"]
    # Life category selects from warm_memory or magazine_left (deterministic via hash)
    assert design_json["templateId"] in {"warm_memory", "magazine_left"}
    assert set(design_json) == {
        "photoId",
        "templateId",
        "templateParams",
        "layers",
        "styleTokens",
        "renderPolicy",
    }
    assert design_json["renderPolicy"] == {"mode": "fallback", "allowHtml": False, "allowJavaScript": False}
    assert design_json["styleTokens"]["--kf-accent-color"].startswith("#")

    layers = design_json["layers"]
    assert any(layer["type"] == "image" and layer["source"] == "preview" for layer in layers)
    assert any(layer["type"] == "text" and layer["role"] == "caption" and layer["content"] == "A quiet morning" for layer in layers)
    assert any(layer["type"] == "timeline" and layer["role"] == "taken_at" for layer in layers)
    for layer in layers:
        assert 0 <= layer["zIndex"] <= 100
        if "rect" in layer:
            rect = layer["rect"]
            assert all(0 <= rect[key] <= 1 for key in ("x", "y", "width", "height"))


def test_fallback_slide_design_does_not_invent_caption_without_message(
    client_storage_and_session_factory,
) -> None:
    from app.services.photo_jobs import process_next_photo_job

    client, storage, session_factory = client_storage_and_session_factory
    seed_user(session_factory, username="member")
    login(client, "member")
    response = client.post(
        "/api/photos/upload",
        data={"category": "pet"},
        files={"file": ("pet.jpg", image_bytes(), "image/jpeg")},
    )
    assert response.status_code == 201
    photo = response.json()

    with session_factory() as db:
        assert process_next_photo_job(db, storage) is True

    design = client.get(f"/api/photos/{photo['id']}/slide-design").json()["design_json"]

    # Pet category selects from pet_portrait, minimal_white, or warm_memory
    assert design["templateId"] in {"pet_portrait", "minimal_white", "warm_memory"}
    assert not any(layer["type"] == "text" and layer.get("role") == "caption" for layer in design["layers"])
    assert any(layer["type"] == "timeline" for layer in design["layers"])


def test_fallback_slide_design_uses_category_and_orientation(
    client_storage_and_session_factory,
) -> None:
    from app.services.photo_jobs import process_next_photo_job

    client, storage, session_factory = client_storage_and_session_factory
    seed_user(session_factory, username="member")
    login(client, "member")
    response = client.post(
        "/api/photos/upload",
        data={"category": "travel", "user_message": "Portrait from a trip"},
        files={"file": ("portrait.jpg", oriented_jpeg_bytes(), "image/jpeg")},
    )
    assert response.status_code == 201
    photo = response.json()

    with session_factory() as db:
        assert process_next_photo_job(db, storage) is True

    design = client.get(f"/api/photos/{photo['id']}/slide-design").json()["design_json"]

    # Travel category selects from poetic_landscape, cinematic_fullscreen, or dark_exhibition
    assert design["templateId"] in {"poetic_landscape", "cinematic_fullscreen", "dark_exhibition"}
    assert design["templateParams"]["orientation"] == "portrait"
    assert design["templateParams"]["imageRect"]["width"] < 0.7
    assert design["templateParams"]["imageRect"]["height"] > 0.8


def test_worker_applies_exif_orientation_to_metadata_thumbnail_and_preview(
    client_storage_and_session_factory,
) -> None:
    from app.services.photo_jobs import process_next_photo_job

    client, storage, session_factory = client_storage_and_session_factory
    seed_user(session_factory, username="member")
    login(client, "member")
    response = client.post(
        "/api/photos/upload",
        data={"category": "travel"},
        files={"file": ("portrait.jpg", oriented_jpeg_bytes(), "image/jpeg")},
    )
    assert response.status_code == 201
    payload = response.json()

    with session_factory() as db:
        assert process_next_photo_job(db, storage) is True

    detail = client.get(f"/api/photos/{payload['id']}").json()
    assert detail["width"] == 20
    assert detail["height"] == 40

    with Image.open(BytesIO(storage.objects[payload["object_key_thumbnail"]])) as thumbnail:
        assert thumbnail.size == (20, 40)
    with Image.open(BytesIO(storage.objects[payload["object_key_preview"]])) as preview:
        assert preview.size == (20, 40)


def test_batch_upload_all_success_creates_independent_results(client_storage_and_session_factory) -> None:
    client, storage, session_factory = client_storage_and_session_factory
    seed_user(session_factory, username="member")
    login(client, "member")

    response = client.post(
        "/api/photos/batch-upload",
        data={"category": "life", "user_message": "Batch upload"},
        files=[
            ("files", ("one.jpg", image_bytes(size=(12, 8)), "image/jpeg")),
            ("files", ("two.jpg", image_bytes(size=(13, 9)), "image/jpeg")),
        ],
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["success_count"] == 2
    assert payload["failure_count"] == 0
    assert [item["filename"] for item in payload["results"]] == ["one.jpg", "two.jpg"]
    assert all(item["success"] is True for item in payload["results"])
    assert all(item["photo"]["status"] == "processing" for item in payload["results"])
    assert all(item["error"] is None for item in payload["results"])
    assert len(storage.objects) == 2


def test_batch_upload_returns_per_file_errors_for_partial_failure(
    client_storage_and_session_factory,
) -> None:
    client, storage, session_factory = client_storage_and_session_factory
    seed_user(session_factory, username="member")
    login(client, "member")
    valid_image = image_bytes(size=(12, 8))
    too_large = b"x" * (1024 * 1024 + 1)

    response = client.post(
        "/api/photos/batch-upload",
        data={"category": "life"},
        files=[
            ("files", ("ok.jpg", valid_image, "image/jpeg")),
            ("files", ("duplicate.jpg", valid_image, "image/jpeg")),
            ("files", ("bad.gif", b"not-a-supported-format", "image/gif")),
            ("files", ("too-large.jpg", too_large, "image/jpeg")),
        ],
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["success_count"] == 1
    assert payload["failure_count"] == 3
    assert [item["success"] for item in payload["results"]] == [True, False, False, False]
    assert payload["results"][1]["error"] == "Duplicate photo"
    assert payload["results"][2]["error"] == "Unsupported image MIME type"
    assert payload["results"][3]["error"] == "File too large"
    assert len(storage.objects) == 1


def test_batch_upload_rejects_more_than_ten_files(client_storage_and_session_factory) -> None:
    client, storage, session_factory = client_storage_and_session_factory
    seed_user(session_factory, username="member")
    login(client, "member")

    response = client.post(
        "/api/photos/batch-upload",
        data={"category": "life"},
        files=[
            ("files", (f"{index}.jpg", image_bytes(size=(12 + index, 8)), "image/jpeg"))
            for index in range(11)
        ],
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Batch upload supports at most 10 files"
    assert storage.objects == {}


def test_worker_failure_retries_then_marks_photo_failed(client_storage_and_session_factory) -> None:
    from app.services.photo_jobs import process_next_photo_job

    client, storage, session_factory = client_storage_and_session_factory
    seed_user(session_factory, username="member")
    login(client, "member")
    response = client.post(
        "/api/photos/upload",
        data={"category": "life"},
        files={"file": ("broken.jpg", b"not-an-image", "image/jpeg")},
    )
    assert response.status_code == 201
    payload = response.json()

    with session_factory() as db:
        assert process_next_photo_job(db, storage) is True

    retry_status = client.get(f"/api/photos/{payload['id']}/processing-status").json()
    assert retry_status["photo_status"] == "processing"
    assert retry_status["job_status"] == "pending"
    assert retry_status["attempts"] == 1
    assert retry_status["error_message"] == "Unsupported or invalid image file"

    with session_factory() as db:
        assert process_next_photo_job(db, storage) is True
        assert process_next_photo_job(db, storage) is True

    failed_status = client.get(f"/api/photos/{payload['id']}/processing-status").json()
    assert failed_status["photo_status"] == "failed"
    assert failed_status["job_status"] == "failed"
    assert failed_status["attempts"] == 3
    assert failed_status["max_attempts"] == 3
    assert failed_status["error_message"] == "Unsupported or invalid image file"
    assert payload["object_key_original"] in storage.objects
    assert payload["object_key_thumbnail"] not in storage.objects
    assert payload["object_key_preview"] not in storage.objects


def test_duplicate_upload_returns_conflict(client_storage_and_session_factory) -> None:
    client, _storage, session_factory = client_storage_and_session_factory
    seed_user(session_factory, username="member")
    login(client, "member")

    upload_test_photo(client)
    response = client.post(
        "/api/photos/upload",
        data={"category": "life"},
        files={"file": ("photo.jpg", image_bytes(), "image/jpeg")},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Duplicate photo"


def test_photos_require_login(client_storage_and_session_factory) -> None:
    client, _storage, _session_factory = client_storage_and_session_factory

    list_response = client.get("/api/photos")
    upload_response = client.post(
        "/api/photos/upload",
        data={"category": "life"},
        files={"file": ("photo.jpg", image_bytes(), "image/jpeg")},
    )

    assert list_response.status_code == 401
    assert upload_response.status_code == 401


def test_upload_rejects_unsupported_mime_type(client_storage_and_session_factory) -> None:
    client, _storage, session_factory = client_storage_and_session_factory
    seed_user(session_factory, username="member")
    login(client, "member")

    response = client.post(
        "/api/photos/upload",
        data={"category": "life"},
        files={"file": ("photo.gif", b"not-a-photo", "image/gif")},
    )

    assert response.status_code == 415


def test_upload_rejects_heic_for_v0(client_storage_and_session_factory) -> None:
    client, _storage, session_factory = client_storage_and_session_factory
    seed_user(session_factory, username="member")
    login(client, "member")

    response = client.post(
        "/api/photos/upload",
        data={"category": "life"},
        files={"file": ("photo.heic", b"not-yet-supported", "image/heic")},
    )

    assert response.status_code == 415
    assert response.json()["detail"] == "HEIC/HEIF conversion is not available"


def test_batch_upload_reports_heic_conversion_unavailable_per_file(
    client_storage_and_session_factory,
) -> None:
    client, storage, session_factory = client_storage_and_session_factory
    seed_user(session_factory, username="member")
    login(client, "member")

    response = client.post(
        "/api/photos/batch-upload",
        data={"category": "life"},
        files=[("files", ("photo.heic", b"not-yet-supported", "image/heic"))],
    )

    assert response.status_code == 201
    assert response.json()["results"][0]["error"] == "HEIC/HEIF conversion is not available"
    assert storage.objects == {}


def test_member_can_view_all_but_not_update_others_photo(client_storage_and_session_factory) -> None:
    client, _storage, session_factory = client_storage_and_session_factory
    seed_user(session_factory, username="owner")
    seed_user(session_factory, username="viewer")
    login(client, "owner")
    photo = upload_test_photo(client)
    client.cookies.clear()

    login(client, "viewer")
    list_response = client.get("/api/photos")
    detail_response = client.get(f"/api/photos/{photo['id']}")
    patch_response = client.patch(f"/api/photos/{photo['id']}", json={"category": "travel"})

    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()] == [photo["id"]]
    assert detail_response.status_code == 200
    assert patch_response.status_code == 403


def test_member_cannot_delete_others_photo(client_storage_and_session_factory) -> None:
    client, storage, session_factory = client_storage_and_session_factory
    seed_user(session_factory, username="owner")
    seed_user(session_factory, username="viewer")
    login(client, "owner")
    photo = upload_test_photo(client)
    process_one_photo_job(session_factory, storage)
    client.cookies.clear()

    login(client, "viewer")
    response = client.delete(f"/api/photos/{photo['id']}")

    assert response.status_code == 403
    assert photo["object_key_original"] in storage.objects
    assert photo["object_key_thumbnail"] in storage.objects
    assert photo["object_key_preview"] in storage.objects
    assert client.get(f"/api/photos/{photo['id']}").status_code == 200


def test_owner_can_update_photo(client_storage_and_session_factory) -> None:
    client, _storage, session_factory = client_storage_and_session_factory
    seed_user(session_factory, username="owner")
    login(client, "owner")
    photo = upload_test_photo(client)

    response = client.patch(
        f"/api/photos/{photo['id']}",
        json={"category": "pet", "user_message": "Updated note"},
    )

    assert response.status_code == 200
    assert response.json()["category"] == "pet"
    assert response.json()["final_caption"] == "Updated note"


def test_admin_can_delete_any_photo_and_objects(client_storage_and_session_factory) -> None:
    client, storage, session_factory = client_storage_and_session_factory
    seed_user(session_factory, username="owner")
    seed_user(session_factory, username="admin", role="admin")
    login(client, "owner")
    photo = upload_test_photo(client)
    process_one_photo_job(session_factory, storage)
    assert len(storage.objects) == 3
    client.cookies.clear()

    login(client, "admin")
    response = client.delete(f"/api/photos/{photo['id']}")

    assert response.status_code == 204
    assert storage.objects == {}
    assert client.get("/api/photos").json() == []


def test_presigned_urls_require_login(client_storage_and_session_factory) -> None:
    client, _storage, session_factory = client_storage_and_session_factory
    seed_user(session_factory, username="member")
    login(client, "member")
    photo = upload_test_photo(client)
    client.cookies.clear()

    unauthorized = client.get(f"/api/photos/{photo['id']}/thumbnail-url")
    unauthorized_preview = client.get(f"/api/photos/{photo['id']}/preview-url")
    assert unauthorized.status_code == 401
    assert unauthorized_preview.status_code == 401

    login(client, "member")
    thumbnail = client.get(f"/api/photos/{photo['id']}/thumbnail-url")
    preview = client.get(f"/api/photos/{photo['id']}/preview-url")
    original = client.get(f"/api/photos/{photo['id']}/original-url")

    assert thumbnail.status_code == 200
    assert preview.status_code == 200
    assert original.status_code == 200
    assert photo["object_key_thumbnail"] in thumbnail.json()["url"]
    assert photo["object_key_preview"] in preview.json()["url"]
    assert photo["object_key_original"] in original.json()["url"]
