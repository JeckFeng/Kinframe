"""Admin audit log routes."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict

from app.api.deps import DbSession, get_current_admin
from app.models import User
from app.services.audit_logs import list_audit_logs


router = APIRouter(prefix="/api/admin/audit-logs", tags=["admin-audit"])


class AuditLogItem(BaseModel):
    id: str
    admin_id: str | None
    action: str
    target_type: str
    target_id: str | None
    detail: dict | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuditLogListResponse(BaseModel):
    items: list[AuditLogItem]
    total: int
    limit: int
    offset: int


@router.get("", response_model=AuditLogListResponse)
def get_audit_logs(
    db: DbSession,
    _admin: Annotated[User, Depends(get_current_admin)],
    admin_id: str | None = Query(default=None),
    action: str | None = Query(default=None),
    target_type: str | None = Query(default=None),
    target_id: str | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> AuditLogListResponse:
    """List audit log entries with optional filtering, newest first."""
    rows, total = list_audit_logs(
        db,
        admin_id=admin_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
    return AuditLogListResponse(
        items=[AuditLogItem.model_validate(r) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )
