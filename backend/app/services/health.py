"""Dependency connectivity checks used by the health endpoint."""

from collections.abc import Callable

from minio import Minio
from redis import Redis
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from app.core.config import Settings
from app.schemas.health import ComponentHealth, HealthResponse

HealthCheck = Callable[[Settings], ComponentHealth]


def _database_connect_args(database_url: str) -> dict[str, int]:
    url = make_url(database_url)
    if url.drivername.startswith("postgresql"):
        return {"connect_timeout": 2}
    return {}


def check_database(settings: Settings) -> ComponentHealth:
    """Check whether the configured database accepts a simple query."""

    engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
        connect_args=_database_connect_args(settings.database_url),
    )
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return ComponentHealth(status="ok")
    except Exception as exc:  # pragma: no cover - exact driver errors vary.
        return ComponentHealth(status="error", detail=str(exc))
    finally:
        engine.dispose()


def check_redis(settings: Settings) -> ComponentHealth:
    """Check whether Redis responds to PING."""

    client = Redis.from_url(
        settings.redis_url,
        socket_connect_timeout=2,
        socket_timeout=2,
        decode_responses=True,
    )
    try:
        client.ping()
        return ComponentHealth(status="ok")
    except Exception as exc:  # pragma: no cover - exact driver errors vary.
        return ComponentHealth(status="error", detail=str(exc))
    finally:
        client.close()


def check_minio(settings: Settings) -> ComponentHealth:
    """Check whether MinIO is reachable with configured credentials."""

    client = Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )
    try:
        bucket_names = {bucket.name for bucket in client.list_buckets()}
    except Exception as exc:  # pragma: no cover - exact client errors vary.
        return ComponentHealth(status="error", detail=str(exc))

    if settings.minio_bucket in bucket_names:
        return ComponentHealth(status="ok", detail="bucket exists")
    return ComponentHealth(status="ok", detail="reachable; bucket missing")


def check_health(settings: Settings) -> HealthResponse:
    """Run all v0 dependency checks and aggregate their statuses."""

    checks: dict[str, HealthCheck] = {
        "database": check_database,
        "redis": check_redis,
        "minio": check_minio,
    }
    results = {name: check(settings) for name, check in checks.items()}
    overall = "ok" if all(result.status == "ok" for result in results.values()) else "degraded"
    return HealthResponse(status=overall, **results)
