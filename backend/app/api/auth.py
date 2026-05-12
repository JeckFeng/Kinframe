"""Authentication API routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api.deps import AppSettings, DbSession, get_current_user
from app.core.security import create_session_token
from app.models import User
from app.schemas.auth import LoginRequest, LoginResponse, MeResponse
from app.schemas.user import UserRead
from app.services.users import authenticate_user, record_login

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    response: Response,
    db: DbSession,
    settings: AppSettings,
) -> LoginResponse:
    """Authenticate a user and set a signed session cookie."""

    user = authenticate_user(db, payload.username, payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    user = record_login(db, user)
    max_age = settings.session_expire_days * 24 * 60 * 60
    token = create_session_token(user.id, settings.app_secret_key, settings.session_expire_days)
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=max_age,
        httponly=True,
        secure=settings.app_env == "production",
        samesite="lax",
    )
    return LoginResponse(user=UserRead.model_validate(user))


@router.post("/logout")
def logout(response: Response, settings: AppSettings) -> dict[str, bool]:
    """Clear the current session cookie."""

    response.delete_cookie(
        key=settings.session_cookie_name,
        httponly=True,
        secure=settings.app_env == "production",
        samesite="lax",
    )
    return {"ok": True}


@router.get("/me", response_model=MeResponse)
def me(current_user: Annotated[User, Depends(get_current_user)]) -> MeResponse:
    """Return the current authenticated user."""

    return MeResponse(user=UserRead.model_validate(current_user))
