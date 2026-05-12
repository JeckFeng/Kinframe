"""Tests for authentication and administrator user APIs."""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings, get_settings
from app.core.database import Base, get_db
from app.main import create_app
from app.schemas.user import UserCreate
from app.services.users import create_user


@pytest.fixture()
def client_and_session_factory() -> Generator[tuple[TestClient, sessionmaker[Session]], None, None]:
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
        minio_bucket="kinframe-photos",
        session_cookie_name="kinframe_test_session",
        session_expire_days=30,
    )

    def override_get_db() -> Generator[Session, None, None]:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    def override_get_settings() -> Settings:
        return settings

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_settings] = override_get_settings

    with TestClient(app) as client:
        yield client, TestingSessionLocal

    Base.metadata.drop_all(bind=engine)


def seed_user(
    session_factory: sessionmaker[Session],
    *,
    username: str,
    password: str = "password123",
    role: str = "member",
    is_active: bool = True,
) -> None:
    with session_factory() as db:
        create_user(
            db,
            UserCreate(
                username=username,
                display_name=username.title(),
                password=password,
                role=role,  # type: ignore[arg-type]
                is_active=is_active,
            ),
        )


def test_login_sets_session_cookie_and_me_returns_user(client_and_session_factory) -> None:
    client, session_factory = client_and_session_factory
    seed_user(session_factory, username="member")

    response = client.post(
        "/api/auth/login",
        json={"username": "member", "password": "password123"},
    )

    assert response.status_code == 200
    assert response.json()["user"]["username"] == "member"
    assert "kinframe_test_session" in response.cookies

    me_response = client.get("/api/auth/me")
    assert me_response.status_code == 200
    assert me_response.json()["user"]["role"] == "member"


def test_login_rejects_bad_password(client_and_session_factory) -> None:
    client, session_factory = client_and_session_factory
    seed_user(session_factory, username="member")

    response = client.post(
        "/api/auth/login",
        json={"username": "member", "password": "wrong-password"},
    )

    assert response.status_code == 401


def test_me_requires_login(client_and_session_factory) -> None:
    client, _session_factory = client_and_session_factory

    response = client.get("/api/auth/me")

    assert response.status_code == 401


def test_member_cannot_access_admin_users(client_and_session_factory) -> None:
    client, session_factory = client_and_session_factory
    seed_user(session_factory, username="member", role="member")

    client.post("/api/auth/login", json={"username": "member", "password": "password123"})
    response = client.get("/api/admin/users")

    assert response.status_code == 403


def test_admin_can_create_and_list_users(client_and_session_factory) -> None:
    client, session_factory = client_and_session_factory
    seed_user(session_factory, username="admin", role="admin")

    login_response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "password123"},
    )
    assert login_response.status_code == 200

    create_response = client.post(
        "/api/admin/users",
        json={
            "username": "new_member",
            "display_name": "New Member",
            "password": "password123",
            "role": "member",
            "is_active": True,
        },
    )

    assert create_response.status_code == 201
    assert create_response.json()["username"] == "new_member"

    list_response = client.get("/api/admin/users")
    assert list_response.status_code == 200
    assert [user["username"] for user in list_response.json()] == ["admin", "new_member"]


def test_admin_create_user_rejects_duplicate_username(client_and_session_factory) -> None:
    client, session_factory = client_and_session_factory
    seed_user(session_factory, username="admin", role="admin")
    seed_user(session_factory, username="member", role="member")
    client.post("/api/auth/login", json={"username": "admin", "password": "password123"})

    response = client.post(
        "/api/admin/users",
        json={
            "username": "member",
            "display_name": "Member Again",
            "password": "password123",
            "role": "member",
        },
    )

    assert response.status_code == 409
