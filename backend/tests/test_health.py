"""Tests for the health endpoint."""

from app.api import health as health_api
from app.main import create_app
from app.schemas.health import ComponentHealth, HealthResponse
from tests.http_client import TestClient


def test_health_endpoint_returns_dependency_status(monkeypatch) -> None:
    def fake_check_health(_settings) -> HealthResponse:
        return HealthResponse(
            status="ok",
            database=ComponentHealth(status="ok"),
            redis=ComponentHealth(status="ok"),
            minio=ComponentHealth(status="ok", detail="reachable; bucket missing"),
        )

    monkeypatch.setattr(health_api, "check_health", fake_check_health)

    with TestClient(create_app()) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "database": {"status": "ok", "detail": None},
        "redis": {"status": "ok", "detail": None},
        "minio": {"status": "ok", "detail": "reachable; bucket missing"},
    }
