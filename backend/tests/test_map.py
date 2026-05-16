"""Tests for v0.4 map data API."""

from collections.abc import Generator

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_object_storage
from app.core.config import Settings, get_settings
from app.core.database import Base, get_db
from app.main import create_app
from app.schemas.user import UserCreate
from app.services.storage import ObjectStorage
from app.services.users import create_user
from tests.http_client import TestClient


class FakeObjectStorage(ObjectStorage):
    """In-memory object storage for map API tests."""

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
def client_and_session_factory() -> Generator[
    tuple[TestClient, sessionmaker[Session]],
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
        yield client, TestingSessionLocal

    Base.metadata.drop_all(bind=engine)


def seed_user(
    session_factory: sessionmaker[Session],
    *,
    username: str,
    password: str = "password123",
    role: str = "member",
) -> str:
    with session_factory() as db:
        user = create_user(
            db,
            UserCreate(
                username=username,
                display_name=username.title(),
                password=password,
                role=role,  # type: ignore[arg-type]
                is_active=True,
            ),
        )
        return user.id


def login(client: TestClient, username: str, password: str = "password123") -> None:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200


def seed_geocoded_photo(
    session_factory: sessionmaker[Session],
    *,
    photo_id: str,
    owner_id: str,
    category: str = "life",
    gps_lat: float | None = 30.5728,
    gps_lng: float | None = 104.0668,
    geocoding_status: str = "succeeded",
    location_city: str | None = "成都市",
    location_region: str | None = "四川省",
    location_country: str | None = "中国",
    final_caption: str | None = "测试文案",
    status: str = "ready",
    taken_at: str = "2025-03-15T06:30:00+00:00",
) -> None:
    with session_factory() as db:
        db.execute(
            text(
                """INSERT INTO photos
                (id, owner_id, category, category_source, caption_source,
                 final_caption, time_source, bucket, object_key_original,
                 object_key_thumbnail, object_key_preview, mime_type,
                 file_size, sha256, taken_at, uploaded_at, created_at, updated_at,
                 gps_lat, gps_lng, geocoding_status, geocoding_provider, geocoded_at,
                 location_city, location_region, location_country, status,
                 ai_caption_enabled, ai_category_enabled, include_in_showcase)
                VALUES
                (:id, :owner_id, :category, 'user', 'user',
                 :final_caption, 'uploaded_at', 'test-photos', 'originals/test/o',
                 'thumbnails/test/t', 'previews/test/p', 'image/jpeg',
                 1024, :sha256, :taken_at, :uploaded_at, :created_at, :updated_at,
                 :gps_lat, :gps_lng, :geocoding_status, :geocoding_provider, :geocoded_at,
                 :location_city, :location_region, :location_country, :status,
                 false, false, true)"""
            ),
            {
                "id": photo_id,
                "owner_id": owner_id,
                "category": category,
                "final_caption": final_caption,
                "sha256": f"fake-{photo_id}",
                "taken_at": taken_at,
                "uploaded_at": taken_at,
                "created_at": taken_at,
                "updated_at": taken_at,
                "gps_lat": gps_lat,
                "gps_lng": gps_lng,
                "geocoding_status": geocoding_status,
                "geocoding_provider": "nominatim",
                "geocoded_at": taken_at,
                "location_city": location_city,
                "location_region": location_region,
                "location_country": location_country,
                "status": status,
            },
        )
        db.commit()


# ── TDD Cycle 1: Unauthenticated request returns 401 ──────────────────

def test_map_photos_requires_auth(
    client_and_session_factory: tuple[TestClient, sessionmaker[Session]],
) -> None:
    """GET /api/map/photos without session cookie returns 401."""
    client, _sf = client_and_session_factory
    response = client.get("/api/map/photos")
    assert response.status_code == 401


# ── TDD Cycle 2: Authenticated request with no data returns empty list ──

def test_map_photos_empty_when_no_geocoded_photos(
    client_and_session_factory: tuple[TestClient, sessionmaker[Session]],
) -> None:
    """GET /api/map/photos returns 200 with empty photos list."""
    client, sf = client_and_session_factory
    seed_user(sf, username="mapper")
    login(client, "mapper")

    response = client.get("/api/map/photos")
    assert response.status_code == 200
    data = response.json()
    assert "photos" in data
    assert data["photos"] == []


# ── TDD Cycle 3: Only geocoding_status='succeeded' photos are returned ──

def test_map_photos_excludes_non_geocoded(
    client_and_session_factory: tuple[TestClient, sessionmaker[Session]],
) -> None:
    """Photos with geocoding_status != 'succeeded' are excluded."""
    client, sf = client_and_session_factory
    owner_id = seed_user(sf, username="mapper3")
    login(client, "mapper3")

    seed_geocoded_photo(sf, photo_id="geo-pending", owner_id=owner_id,
                        geocoding_status="pending")
    seed_geocoded_photo(sf, photo_id="geo-failed", owner_id=owner_id,
                        geocoding_status="failed")
    seed_geocoded_photo(sf, photo_id="geo-success", owner_id=owner_id,
                        geocoding_status="succeeded")

    response = client.get("/api/map/photos")
    assert response.status_code == 200
    data = response.json()
    photo_ids = [p["photo_id"] for p in data["photos"]]
    assert "geo-success" in photo_ids
    assert "geo-pending" not in photo_ids
    assert "geo-failed" not in photo_ids


# ── TDD Cycle 4: Category filter via ?category= query parameter ──

def test_map_photos_filter_by_category(
    client_and_session_factory: tuple[TestClient, sessionmaker[Session]],
) -> None:
    """GET /api/map/photos?category=life returns only life photos."""
    client, sf = client_and_session_factory
    owner_id = seed_user(sf, username="mapper4")
    login(client, "mapper4")

    seed_geocoded_photo(sf, photo_id="cat-life", owner_id=owner_id, category="life")
    seed_geocoded_photo(sf, photo_id="cat-photography", owner_id=owner_id, category="photography")
    seed_geocoded_photo(sf, photo_id="cat-pet", owner_id=owner_id, category="pet")

    response = client.get("/api/map/photos?category=life")
    assert response.status_code == 200
    data = response.json()
    photo_ids = [p["photo_id"] for p in data["photos"]]
    assert "cat-life" in photo_ids
    assert "cat-photography" not in photo_ids
    assert "cat-pet" not in photo_ids


# ── TDD Cycle 5: Exclude photos with status != 'ready' ──

def test_map_photos_excludes_non_ready(
    client_and_session_factory: tuple[TestClient, sessionmaker[Session]],
) -> None:
    """Photos with status != 'ready' are excluded from map results."""
    client, sf = client_and_session_factory
    owner_id = seed_user(sf, username="mapper5")
    login(client, "mapper5")

    seed_geocoded_photo(sf, photo_id="st-ready", owner_id=owner_id, status="ready")
    seed_geocoded_photo(sf, photo_id="st-processing", owner_id=owner_id, status="processing")
    seed_geocoded_photo(sf, photo_id="st-failed", owner_id=owner_id, status="failed")

    response = client.get("/api/map/photos")
    assert response.status_code == 200
    data = response.json()
    photo_ids = [p["photo_id"] for p in data["photos"]]
    assert "st-ready" in photo_ids
    assert "st-processing" not in photo_ids
    assert "st-failed" not in photo_ids


# ── TDD Cycle 6: Exclude photos without GPS coordinates ──

def test_map_photos_excludes_null_gps(
    client_and_session_factory: tuple[TestClient, sessionmaker[Session]],
) -> None:
    """Photos with NULL gps_lat or gps_lng are excluded."""
    client, sf = client_and_session_factory
    owner_id = seed_user(sf, username="mapper6")
    login(client, "mapper6")

    seed_geocoded_photo(sf, photo_id="gps-both-null", owner_id=owner_id,
                        gps_lat=None, gps_lng=None, geocoding_status="not_applicable")
    seed_geocoded_photo(sf, photo_id="gps-lat-null", owner_id=owner_id,
                        gps_lat=None, gps_lng=104.0, geocoding_status="succeeded")
    seed_geocoded_photo(sf, photo_id="gps-lng-null", owner_id=owner_id,
                        gps_lat=30.0, gps_lng=None, geocoding_status="succeeded")
    seed_geocoded_photo(sf, photo_id="gps-ok", owner_id=owner_id,
                        gps_lat=30.5728, gps_lng=104.0668)

    response = client.get("/api/map/photos")
    assert response.status_code == 200
    data = response.json()
    photo_ids = [p["photo_id"] for p in data["photos"]]
    assert "gps-ok" in photo_ids
    assert "gps-both-null" not in photo_ids
    assert "gps-lat-null" not in photo_ids
    assert "gps-lng-null" not in photo_ids


# ── TDD Cycle 7: Presigned URL format and full field verification ──

def test_map_photos_response_fields(
    client_and_session_factory: tuple[TestClient, sessionmaker[Session]],
) -> None:
    """Each map photo item contains presigned URLs and all expected fields."""
    client, sf = client_and_session_factory
    owner_id = seed_user(sf, username="mapper7")
    login(client, "mapper7")

    seed_geocoded_photo(
        sf, photo_id="field-test", owner_id=owner_id,
        category="photography",
        gps_lat=30.5728, gps_lng=104.0668,
        location_city="成都市", location_region="四川省", location_country="中国",
        final_caption="测试文案", taken_at="2025-03-15T06:30:00+00:00",
    )

    response = client.get("/api/map/photos")
    assert response.status_code == 200
    data = response.json()
    assert len(data["photos"]) == 1

    item = data["photos"][0]
    assert item["photo_id"] == "field-test"
    assert item["preview_url"].startswith("https://storage.test/")
    assert "expires=" in item["preview_url"]
    assert item["thumbnail_url"].startswith("https://storage.test/")
    assert "expires=" in item["thumbnail_url"]
    assert item["category"] == "photography"
    assert item["gps_lat"] == 30.5728
    assert item["gps_lng"] == 104.0668
    assert item["location_city"] == "成都市"
    assert item["location_region"] == "四川省"
    assert item["location_country"] == "中国"
    assert item["final_caption"] == "测试文案"
    assert item["taken_at"] is not None
