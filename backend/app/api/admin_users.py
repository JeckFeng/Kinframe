"""Administrator user management routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import DbSession, get_current_admin
from app.models import User
from app.schemas.user import UserCreate, UserRead
from app.services.users import DuplicateUsernameError, create_user, list_users

router = APIRouter(prefix="/api/admin/users", tags=["admin-users"])


@router.get("", response_model=list[UserRead])
def get_users(
    db: DbSession,
    _admin: Annotated[User, Depends(get_current_admin)],
) -> list[UserRead]:
    """List all user accounts."""

    return [UserRead.model_validate(user) for user in list_users(db)]


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def post_user(
    payload: UserCreate,
    db: DbSession,
    _admin: Annotated[User, Depends(get_current_admin)],
) -> UserRead:
    """Create a user account."""

    try:
        user = create_user(db, payload)
    except DuplicateUsernameError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists",
        ) from exc
    return UserRead.model_validate(user)
