"""User account service functions."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models import User
from app.schemas.user import UserCreate


class DuplicateUsernameError(ValueError):
    """Raised when creating a user with an existing username."""


def get_user_by_id(db: Session, user_id: str) -> User | None:
    """Return a user by ID."""

    return db.get(User, user_id)


def get_user_by_username(db: Session, username: str) -> User | None:
    """Return a user by username."""

    return db.scalar(select(User).where(User.username == username))


def list_users(db: Session) -> list[User]:
    """Return all users ordered by creation time."""

    return list(db.scalars(select(User).order_by(User.created_at.asc(), User.username.asc())))


def create_user(db: Session, payload: UserCreate) -> User:
    """Create a new user account."""

    user = User(
        username=payload.username,
        display_name=payload.display_name,
        password_hash=hash_password(payload.password),
        role=payload.role,
        is_active=payload.is_active,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DuplicateUsernameError(payload.username) from exc
    db.refresh(user)
    return user


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    """Return the active user matching username and password."""

    user = get_user_by_username(db, username)
    if user is None or not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def record_login(db: Session, user: User) -> User:
    """Update the user's last login timestamp."""

    user.last_login_at = datetime.now(timezone.utc)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
