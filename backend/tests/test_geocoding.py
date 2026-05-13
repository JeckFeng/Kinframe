"""Tests for v0.2 reverse geocoding service and worker integration."""

from collections.abc import Generator
from datetime import datetime, timezone
from io import BytesIO
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_object_storage
from app.core.config import Settings, get_settings
from app.core.database import Base, get_db
from app.main import create_app
from app.models import Photo, PhotoProcessingJob
from app.schemas.user import UserCreate
from app.services.exif import ExtractedMetadata
from app.services.geocoding import (
    GeocodingResult,
    GeocodingService,
    NoopProvider,
    create_geocoding_service,
)
from app.services.photo_jobs import (
    PHOTO_JOB_TYPE_REVERSE_GEOCODE,
    process_next_photo_job,
)
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


class MockGeocodingProvider:
    """Controllable geocoding provider for integration tests."""

    def __init__(self) -> None:
        self.calls: list[tuple[float, float]] = []
        self.result: GeocodingResult | None = None
        self.should_fail: bool = False

    def reverse_geocode(self, lat: float, lng: float) -> GeocodingResult | None:
        self.calls.append((lat, lng))
        if self.should_fail:
            raise RuntimeError("Simulated geocoding failure")
        return self.result


@pytest.fixture()
def worker_db_factory() -> Generator[
    tuple[sessionmaker[Session], FakeObjectStorage],
    None,
    None,
]:
    """DB + storage fixture for worker-level tests (no HTTP API)."""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    storage = FakeObjectStorage()
    yield TestingSessionLocal, storage
    Base.metadata.drop_all(bind=engine)


def _seed_user(db: Session, username: str = "member", password: str = "password123", role: str = "member") -> str:
    user = create_user(db, UserCreate(username=username, display_name=username, password=password, role=role, is_active=True))
    return str(user.id)


def _create_photo_with_gps(db: Session, storage: FakeObjectStorage, owner_id: str, gps_lat: float | None, gps_lng: float | None) -> Photo:
    """Insert a photo record with GPS and a mock object in storage."""
    import uuid
    from app.services.photos import PHOTO_STATUS_READY

    photo_id = str(uuid.uuid4())
    original_key = f"originals/2026/05/{photo_id}.jpg"
    thumbnail_key = f"thumbnails/2026/05/{photo_id}_512.webp"
    preview_key = f"previews/2026/05/{photo_id}.webp"

    # Put fake image bytes in storage so downloads don't fail
    fake_bytes = b"fake-image-bytes"
    storage.upload_bytes(original_key, fake_bytes, "image/jpeg")

    photo = Photo(
        id=photo_id,
        owner_id=owner_id,
        category="life",
        category_source="user",
        bucket="test-photos",
        object_key_original=original_key,
        object_key_thumbnail=thumbnail_key,
        object_key_preview=preview_key,
        mime_type="image/jpeg",
        file_size=len(fake_bytes),
        sha256="test-sha256",
        status=PHOTO_STATUS_READY,
        width=100,
        height=80,
        gps_lat=gps_lat,
        gps_lng=gps_lng,
        taken_at=datetime.now(timezone.utc),
        uploaded_at=datetime.now(timezone.utc),
        exif_json=None,
        geocoding_status="not_applicable",
    )
    db.add(photo)
    db.commit()
    db.refresh(photo)
    return photo


# ── Unit tests ────────────────────────────────────────────────────


class TestNoopProvider:
    def test_returns_none(self):
        provider = NoopProvider()
        assert provider.reverse_geocode(39.9042, 116.4074) is None


class TestGeocodingResult:
    def test_all_fields_default_to_none(self):
        result = GeocodingResult()
        assert result.name is None
        assert result.country is None
        assert result.region is None
        assert result.city is None
        assert result.district is None
        assert result.road is None

    def test_partial_result(self):
        result = GeocodingResult(country="China", city="Beijing")
        assert result.country == "China"
        assert result.city == "Beijing"
        assert result.name is None


class TestGeocodingService:
    def test_disabled_service_returns_none(self):
        service = GeocodingService(
            _provider=NoopProvider(),
            _enabled=False,
            _provider_name="noop",
            _rate_limit_interval=0.0,
        )
        assert service.reverse_geocode(39.9042, 116.4074) is None

    def test_caches_same_coordinates(self):
        mock = MockGeocodingProvider()
        mock.result = GeocodingResult(name="Test Place")
        service = GeocodingService(
            _provider=mock,
            _enabled=True,
            _provider_name="test",
            _rate_limit_interval=0.0,
        )
        result1 = service.reverse_geocode(39.9042, 116.4074)
        result2 = service.reverse_geocode(39.90421, 116.40739)  # rounds to same

        assert result1 == result2
        assert len(mock.calls) == 1  # second call used cache

    def test_different_coordinates_make_separate_calls(self):
        mock = MockGeocodingProvider()
        mock.result = GeocodingResult(name="Place")
        service = GeocodingService(
            _provider=mock,
            _enabled=True,
            _provider_name="test",
            _rate_limit_interval=0.0,
        )
        service.reverse_geocode(39.9042, 116.4074)
        service.reverse_geocode(31.2304, 121.4737)

        assert len(mock.calls) == 2

    def test_rate_limit_enforced(self):
        mock = MockGeocodingProvider()
        mock.result = GeocodingResult(name="Place")
        service = GeocodingService(
            _provider=mock,
            _enabled=True,
            _provider_name="test",
            _rate_limit_interval=0.2,  # 200ms
        )
        import time
        start = time.monotonic()
        service.reverse_geocode(39.9042, 116.4074)
        service.reverse_geocode(31.2304, 121.4737)
        elapsed = time.monotonic() - start
        # Second call should have waited at least ~200ms
        assert elapsed >= 0.18

    def test_provider_exception_bubbles_up(self):
        mock = MockGeocodingProvider()
        mock.should_fail = True
        service = GeocodingService(
            _provider=mock,
            _enabled=True,
            _provider_name="test",
            _rate_limit_interval=0.0,
        )
        with pytest.raises(RuntimeError, match="Simulated geocoding failure"):
            service.reverse_geocode(39.9042, 116.4074)


class TestNominatimProvider:
    def test_maps_osm_address_fields(self):
        from unittest.mock import MagicMock

        from app.core.config import Settings
        from app.services.geocoding import NominatimProvider

        settings = Settings(
            nominatim_endpoint="https://nominatim.example.org",
            geocoding_timeout_seconds=10,
        )
        provider = NominatimProvider(settings)

        mock_response_data = {
            "display_name": "Chang'an Avenue, Dongcheng, Beijing, China",
            "address": {
                "country": "China",
                "state": "Beijing",
                "city": "Beijing",
                "county": "Dongcheng District",
                "road": "Chang'an Avenue",
            },
        }

        mock_client = MagicMock()
        mock_client.get.return_value.raise_for_status.return_value = None
        mock_client.get.return_value.json.return_value = mock_response_data
        with patch.object(provider, "_get_client", return_value=mock_client):
            result = provider.reverse_geocode(39.9042, 116.4074)

        assert result is not None
        assert result.name == "Chang'an Avenue, Dongcheng, Beijing, China"
        assert result.country == "China"
        assert result.region == "Beijing"
        assert result.city == "Beijing"
        assert result.district == "Dongcheng District"
        assert result.road == "Chang'an Avenue"

    def test_returns_none_on_http_error(self):
        from unittest.mock import MagicMock

        import httpx

        from app.core.config import Settings
        from app.services.geocoding import NominatimProvider

        settings = Settings(
            nominatim_endpoint="https://nominatim.example.org",
            geocoding_timeout_seconds=10,
        )
        provider = NominatimProvider(settings)

        mock_client = MagicMock()
        mock_client.get.side_effect = httpx.ConnectError("Connection refused")
        with patch.object(provider, "_get_client", return_value=mock_client):
            result = provider.reverse_geocode(39.9042, 116.4074)

        assert result is None


class TestAmapProvider:
    def test_maps_gaode_address_fields(self):
        from unittest.mock import MagicMock

        from app.core.config import Settings
        from app.services.geocoding import AmapProvider

        settings = Settings(
            amap_api_key="test-amap-key",
            geocoding_timeout_seconds=10,
        )
        provider = AmapProvider(settings)

        mock_response_data = {
            "status": "1",
            "regeocode": {
                "formatted_address": "北京市东城区长安街1号",
                "addressComponent": {
                    "country": "中国",
                    "province": "北京市",
                    "city": "北京市",
                    "district": "东城区",
                    "township": "",
                    "streetNumber": {
                        "street": "长安街",
                        "number": "1号",
                    },
                },
            },
        }

        mock_client = MagicMock()
        mock_client.get.return_value.raise_for_status.return_value = None
        mock_client.get.return_value.json.return_value = mock_response_data
        with patch.object(provider, "_get_client", return_value=mock_client):
            result = provider.reverse_geocode(39.9042, 116.4074)

        assert result is not None
        assert result.name == "北京市东城区长安街1号"
        assert result.country == "中国"
        assert result.region == "北京市"
        assert result.city == "北京市"
        assert result.district == "东城区"
        assert result.road == "长安街1号"

    def test_returns_none_on_non_1_status(self):
        from unittest.mock import MagicMock

        from app.core.config import Settings
        from app.services.geocoding import AmapProvider

        settings = Settings(
            amap_api_key="test-amap-key",
            geocoding_timeout_seconds=10,
        )
        provider = AmapProvider(settings)

        mock_client = MagicMock()
        mock_client.get.return_value.raise_for_status.return_value = None
        mock_client.get.return_value.json.return_value = {"status": "0", "info": "INVALID_USER_KEY"}
        with patch.object(provider, "_get_client", return_value=mock_client):
            result = provider.reverse_geocode(39.9042, 116.4074)

        assert result is None


class TestCreateGeocodingService:
    def test_disabled_yields_noop_provider(self):
        from app.core.config import Settings
        settings = Settings(geocoding_enabled=False, geocoding_provider="nominatim")
        service = create_geocoding_service(settings)
        assert service.enabled is False
        assert service.provider_name == "noop"

    def test_noop_provider_name_yields_disabled(self):
        from app.core.config import Settings
        settings = Settings(geocoding_enabled=True, geocoding_provider="noop")
        service = create_geocoding_service(settings)
        assert service.enabled is False
        assert service.provider_name == "noop"

    def test_enabled_nominatim(self):
        from app.core.config import Settings
        settings = Settings(
            geocoding_enabled=True,
            geocoding_provider="nominatim",
            nominatim_endpoint="https://nominatim.example.org",
        )
        service = create_geocoding_service(settings)
        assert service.enabled is True
        assert service.provider_name == "nominatim"


# ── Integration tests ─────────────────────────────────────────────


class TestReverseGeocodeWorkerFlow:
    def test_no_reverse_geocode_job_when_gps_missing(self, worker_db_factory):
        """Photos without GPS should not trigger reverse geocoding."""
        session_factory, storage = worker_db_factory

        with session_factory() as db:
            owner_id = _seed_user(db)
            photo = _create_photo_with_gps(db, storage, owner_id, gps_lat=None, gps_lng=None)
            photo_id = photo.id

        # Verify geocoding_status is not_applicable for photo without GPS
        with session_factory() as db:
            photo = db.get(Photo, photo_id)
            assert photo is not None
            assert photo.geocoding_status == "not_applicable"

    def test_reverse_geocode_job_created_and_succeeds(self, worker_db_factory):
        """Full flow: photo with GPS → reverse_geocode job → location populated."""
        session_factory, storage = worker_db_factory

        mock_provider = MockGeocodingProvider()
        mock_provider.result = GeocodingResult(
            name="Tiananmen Square, Beijing, China",
            country="China",
            region="Beijing",
            city="Beijing",
            district="Dongcheng",
            road="Chang'an Avenue",
        )
        geocoding = GeocodingService(
            _provider=mock_provider,
            _enabled=True,
            _provider_name="nominatim",
            _rate_limit_interval=0.0,
        )

        with session_factory() as db:
            owner_id = _seed_user(db)
            photo = _create_photo_with_gps(db, storage, owner_id, gps_lat=39.9042, gps_lng=116.4074)
            photo_id = photo.id

            # Manually create a reverse_geocode job (simulating what the
            # ingest pipeline does after detecting GPS)
            from app.services.photo_jobs import create_reverse_geocode_job
            job = create_reverse_geocode_job(
                db,
                photo_id,
                max_attempts=2,
                provider_name="nominatim",
            )
            assert job.job_type == PHOTO_JOB_TYPE_REVERSE_GEOCODE
            assert job.status == "pending"

            # Verify photo geocoding_status updated
            db.refresh(photo)
            assert photo.geocoding_status == "pending"

        # Process the reverse_geocode job
        with session_factory() as db:
            assert process_next_photo_job(db, storage, geocoding=geocoding) is True

        # Verify location fields populated
        with session_factory() as db:
            photo = db.get(Photo, photo_id)
            assert photo is not None
            assert photo.geocoding_status == "succeeded"
            assert photo.geocoding_provider == "nominatim"
            assert photo.location_name == "Tiananmen Square, Beijing, China"
            assert photo.location_country == "China"
            assert photo.location_city == "Beijing"
            assert photo.location_district == "Dongcheng"
            assert photo.location_road == "Chang'an Avenue"
            assert photo.status == "ready"  # CRITICAL: stays ready

            # Job marked succeeded
            jobs = db.scalars(
                select(PhotoProcessingJob).where(
                    PhotoProcessingJob.photo_id == photo_id,
                    PhotoProcessingJob.job_type == PHOTO_JOB_TYPE_REVERSE_GEOCODE,
                )
            ).all()
            assert len(jobs) == 1
            assert jobs[0].status == "succeeded"

    def test_geocoding_failure_keeps_photo_ready(self, worker_db_factory):
        """Geocoding failure must NOT change photo.status away from ready."""
        session_factory, storage = worker_db_factory

        mock_provider = MockGeocodingProvider()
        mock_provider.should_fail = True
        geocoding = GeocodingService(
            _provider=mock_provider,
            _enabled=True,
            _provider_name="nominatim",
            _rate_limit_interval=0.0,
        )

        with session_factory() as db:
            owner_id = _seed_user(db)
            photo = _create_photo_with_gps(db, storage, owner_id, gps_lat=39.9042, gps_lng=116.4074)
            photo_id = photo.id

            from app.services.photo_jobs import create_reverse_geocode_job
            create_reverse_geocode_job(db, photo_id, max_attempts=1, provider_name="nominatim")

        # First attempt — should fail and exhaust (max_attempts=1)
        with session_factory() as db:
            assert process_next_photo_job(db, storage, geocoding=geocoding) is True

        # Verify photo still ready despite geocoding failure
        with session_factory() as db:
            photo = db.get(Photo, photo_id)
            assert photo is not None
            assert photo.status == "ready"  # CRITICAL
            assert photo.geocoding_status == "failed"
            assert "Simulated geocoding failure" in (photo.geocoding_error or "")

    def test_geocoding_disabled_does_not_create_job(self, worker_db_factory):
        """When geocoding is disabled, no follow-on jobs appear."""
        session_factory, storage = worker_db_factory

        disabled_service = GeocodingService(
            _provider=NoopProvider(),
            _enabled=False,
            _provider_name="noop",
            _rate_limit_interval=0.0,
        )

        with session_factory() as db:
            owner_id = _seed_user(db)
            photo = _create_photo_with_gps(db, storage, owner_id, gps_lat=39.9042, gps_lng=116.4074)
            photo_id = photo.id

            from app.services.photo_jobs import create_reverse_geocode_job
            create_reverse_geocode_job(db, photo_id, max_attempts=1, provider_name="noop")

        with session_factory() as db:
            assert process_next_photo_job(db, storage, geocoding=disabled_service) is True

        with session_factory() as db:
            photo = db.get(Photo, photo_id)
            assert photo is not None
            assert photo.status == "ready"  # unchanged
            assert photo.geocoding_status == "failed"
            assert photo.geocoding_error == "Geocoding is disabled"
