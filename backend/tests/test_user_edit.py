"""Tests for v0.3-10: User Self-Service Photo Message Editing."""

from __future__ import annotations

from collections.abc import Generator
from io import BytesIO

import pytest
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models import Photo, User
from app.services.photos import PHOTO_STATUS_READY
from app.services.users import create_user
from app.schemas.user import UserCreate
from app.services.storage import ObjectStorage


# ── Fixtures ────────────────────────────────────────────────────────────

class FakeObjectStorage(ObjectStorage):
    bucket = "test-photos"

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.content_types: dict[str, str] = {}

    def ensure_bucket(self) -> None: pass

    def upload_bytes(self, object_key: str, data: bytes, content_type: str) -> None:
        self.objects[object_key] = data
        self.content_types[object_key] = content_type

    def presigned_get_url(self, object_key: str, expires_seconds: int = 900) -> str:
        return f"https://storage.test/{object_key}"

    def download_bytes(self, object_key: str) -> bytes:
        return self.objects[object_key]

    def delete_object(self, object_key: str) -> None:
        self.objects.pop(object_key, None)
        self.content_types.pop(object_key, None)


@pytest.fixture()
def db() -> Generator[Session, None, None]:
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    with Session(engine) as session:
        session.execute(Base.metadata.tables["categories"].insert().values([
            {"id": "c1", "slug": "life", "name": "生活照", "description": "", "sort_order": 1, "is_active": True},
            {"id": "c2", "slug": "photography", "name": "摄影照", "description": "", "sort_order": 2, "is_active": True},
            {"id": "c3", "slug": "pet", "name": "宠物照", "description": "", "sort_order": 3, "is_active": True},
        ]))
        session.commit()
    yield Session(engine)
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def owner(db: Session) -> User:
    return create_user(db, UserCreate(username="owner", display_name="Owner", password="password123", role="member", is_active=True))


@pytest.fixture()
def other_user(db: Session) -> User:
    return create_user(db, UserCreate(username="other", display_name="Other", password="password123", role="member", is_active=True))


@pytest.fixture()
def admin(db: Session) -> User:
    return create_user(db, UserCreate(username="admin", display_name="Admin", password="password123", role="admin", is_active=True))


@pytest.fixture()
def storage() -> FakeObjectStorage:
    return FakeObjectStorage()


def _make_photo(db: Session, storage: FakeObjectStorage, owner: User, **kwargs) -> Photo:
    import uuid
    photo_id = str(uuid.uuid4())
    original_key = f"originals/2026/05/{photo_id}.jpg"
    img = Image.new("RGB", (64, 48), color=(100, 150, 200))
    buf = BytesIO(); img.save(buf, "JPEG"); fake_bytes = buf.getvalue()
    storage.upload_bytes(original_key, fake_bytes, "image/jpeg")
    from datetime import datetime, timezone
    photo = Photo(
        id=photo_id, owner_id=owner.id, category=kwargs.get("category", "life"),
        bucket="test-photos", object_key_original=original_key,
        object_key_thumbnail=f"thumbnails/2026/05/{photo_id}.webp",
        object_key_preview=f"previews/2026/05/{photo_id}.webp",
        mime_type="image/jpeg", file_size=len(fake_bytes), sha256=f"sha-{photo_id[:8]}",
        status=PHOTO_STATUS_READY, width=100, height=80,
        user_message=kwargs.get("user_message"),
        final_caption=kwargs.get("final_caption", kwargs.get("user_message")),  # respect explicit final_caption
        caption_source=kwargs.get("caption_source", "user" if kwargs.get("user_message") else "none"),
        ai_caption_enabled=False, ai_category_enabled=False,
        taken_at=kwargs.get("taken_at", datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)),
        uploaded_at=kwargs.get("uploaded_at", datetime(2025, 5, 10, 12, 0, 0, tzinfo=timezone.utc)),
        time_source=kwargs.get("time_source", "exif"),
        geocoding_status=kwargs.get("geocoding_status", "not_applicable"),
    )
    db.add(photo); db.commit(); db.refresh(photo)
    return photo


# ── Tests (TDD RED → GREEN) ────────────────────────────────────────────

class TestUserEditMessage:
    def test_owner_can_update_own_message(self, db, owner, storage):
        """Photo owner can PATCH their user_message successfully."""
        photo = _make_photo(db, storage, owner, user_message="Original")
        from app.services.photos import update_user_message
        updated = update_user_message(db, photo, owner, "Updated message")
        assert updated.user_message == "Updated message"
        assert updated.final_caption == "Updated message"
        assert updated.caption_source == "user"

    def test_non_owner_cannot_update_message(self, db, owner, other_user, storage):
        """Non-owner gets 403 when trying to edit another's message."""
        import pytest
        photo = _make_photo(db, storage, owner, user_message="Original")
        from app.services.photos import update_user_message
        from app.services.photos import PhotoPermissionError
        with pytest.raises(PhotoPermissionError):
            update_user_message(db, photo, other_user, "Hacked")

    def test_admin_override_preserved(self, db, owner, storage):
        """When admin has overridden caption, user update keeps admin caption."""
        photo = _make_photo(db, storage, owner, user_message="User msg",
                            caption_source="admin", final_caption="Admin caption")
        from app.services.photos import update_user_message
        updated = update_user_message(db, photo, owner, "New user msg")
        assert updated.user_message == "New user msg"
        # Admin override preserved
        assert updated.final_caption == "Admin caption"
        assert updated.caption_source == "admin"

    def test_no_admin_override_updates_final_caption(self, db, owner, storage):
        """When no admin override, user_message becomes final_caption."""
        photo = _make_photo(db, storage, owner, user_message="Original")
        from app.services.photos import update_user_message
        updated = update_user_message(db, photo, owner, "Fresh caption")
        assert updated.user_message == "Fresh caption"
        assert updated.final_caption == "Fresh caption"
        assert updated.caption_source == "user"

    def test_audit_log_created_on_edit(self, db, owner, storage):
        """Editing message should create an audit log entry."""
        photo = _make_photo(db, storage, owner, user_message="Before")
        from app.services.photos import update_user_message
        updated = update_user_message(db, photo, owner, "After")
        # Verify audit log exists
        from app.models.audit_log import AuditLog
        logs = db.query(AuditLog).filter(
            AuditLog.target_id == photo.id,
            AuditLog.target_type == "photo",
        ).all()
        assert any("user_message" in log.action for log in logs)
