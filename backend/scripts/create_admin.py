"""Create the initial KinFrame administrator account."""

import argparse
from getpass import getpass
from pathlib import Path
import sys

from sqlalchemy.exc import SQLAlchemyError

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.core.database import Base, SessionLocal, engine
from app.models import User
from app.schemas.user import UserCreate
from app.services.users import DuplicateUsernameError, create_user, get_user_by_username


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a KinFrame admin user.")
    parser.add_argument("--username", required=True)
    parser.add_argument("--display-name", required=True)
    parser.add_argument("--password")
    parser.add_argument(
        "--create-tables",
        action="store_true",
        help="Create database tables before creating the admin account. Useful for v0 local setup.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    password = args.password or getpass("Admin password: ")
    if len(password) < 8:
        raise SystemExit("Password must be at least 8 characters.")

    if args.create_tables:
        Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        existing = get_user_by_username(db, args.username)
        if existing is not None:
            raise SystemExit(f"User already exists: {args.username}")

        payload = UserCreate(
            username=args.username,
            display_name=args.display_name,
            password=password,
            role="admin",
            is_active=True,
        )
        try:
            user: User = create_user(db, payload)
        except DuplicateUsernameError as exc:
            raise SystemExit(f"User already exists: {args.username}") from exc
        except SQLAlchemyError as exc:
            raise SystemExit(f"Database error: {exc}") from exc

    print(f"Created admin user: {user.username}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
