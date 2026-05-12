"""Password hashing and signed session token helpers."""

import base64
import hashlib
import hmac
import json
import time
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

_password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """Hash a plaintext password using Argon2."""

    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Return whether a plaintext password matches an Argon2 hash."""

    try:
        return _password_hasher.verify(password_hash, password)
    except (InvalidHashError, VerificationError, VerifyMismatchError):
        return False


def _base64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _base64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def create_session_token(user_id: str, secret_key: str, expire_days: int) -> str:
    """Create a compact HMAC-signed session token for a user ID."""

    payload = {
        "user_id": user_id,
        "exp": int(time.time()) + expire_days * 24 * 60 * 60,
    }
    payload_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    payload_part = _base64url_encode(payload_bytes)
    signature = hmac.new(
        secret_key.encode("utf-8"),
        payload_part.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return f"{payload_part}.{_base64url_encode(signature)}"


def read_session_token(token: str, secret_key: str) -> str | None:
    """Return the user ID from a valid session token, otherwise None."""

    try:
        payload_part, signature_part = token.split(".", maxsplit=1)
    except ValueError:
        return None

    expected_signature = hmac.new(
        secret_key.encode("utf-8"),
        payload_part.encode("ascii"),
        hashlib.sha256,
    ).digest()
    try:
        actual_signature = _base64url_decode(signature_part)
    except (ValueError, TypeError):
        return None

    if not hmac.compare_digest(actual_signature, expected_signature):
        return None

    try:
        payload = json.loads(_base64url_decode(payload_part))
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
        return None

    expires_at = payload.get("exp")
    user_id = payload.get("user_id")
    if not isinstance(expires_at, int) or not isinstance(user_id, str):
        return None
    if expires_at < int(time.time()):
        return None
    return user_id
