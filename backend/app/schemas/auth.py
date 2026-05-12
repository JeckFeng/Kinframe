"""Schemas for authentication APIs."""

from pydantic import BaseModel, Field

from app.schemas.user import UserRead


class LoginRequest(BaseModel):
    """Username and password login request."""

    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class LoginResponse(BaseModel):
    """Login response containing the current user."""

    user: UserRead


class MeResponse(BaseModel):
    """Current session response."""

    user: UserRead
