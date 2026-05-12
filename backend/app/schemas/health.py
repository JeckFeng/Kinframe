"""Schemas for health check responses."""

from typing import Literal

from pydantic import BaseModel

ComponentStatusValue = Literal["ok", "error"]
OverallStatusValue = Literal["ok", "degraded"]


class ComponentHealth(BaseModel):
    """Connectivity status for one backend dependency."""

    status: ComponentStatusValue
    detail: str | None = None


class HealthResponse(BaseModel):
    """Aggregated backend health response."""

    status: OverallStatusValue
    database: ComponentHealth
    redis: ComponentHealth
    minio: ComponentHealth
