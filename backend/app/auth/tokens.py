"""JWT access token and refresh token utilities."""

import hashlib
import secrets
from datetime import timedelta
from uuid import UUID, uuid4

from jose import JWTError, jwt

from app.auth.errors import TokenExpiredError, TokenInvalidError
from app.common.config import get_settings
from app.common.utils import utcnow


def create_access_token(user_id: UUID, email: str, role: str) -> tuple[str, int]:
    """Create a JWT access token with expiry.

    Returns (token_string, expires_in_seconds).
    """
    settings = get_settings()
    expires_in = settings.auth_access_token_expire_minutes * 60
    now = utcnow()
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "exp": now + timedelta(minutes=settings.auth_access_token_expire_minutes),
        "iat": now,
        "jti": str(uuid4()),
    }
    token = jwt.encode(payload, settings.auth_jwt_secret_key, algorithm=settings.auth_jwt_algorithm)
    return token, expires_in


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT access token.

    Returns the payload dict with keys: sub, email, role, exp, iat, jti.
    Raises TokenExpiredError or TokenInvalidError.
    """
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.auth_jwt_secret_key,
            algorithms=[settings.auth_jwt_algorithm],
        )
        return payload
    except JWTError as e:
        if "expired" in str(e).lower():
            raise TokenExpiredError() from e
        raise TokenInvalidError() from e


def generate_refresh_token() -> tuple[str, str]:
    """Generate a refresh token and its SHA-256 hash.

    Returns (plaintext_token, sha256_hash).
    """
    plaintext = secrets.token_urlsafe(48)
    token_hash = hash_refresh_token(plaintext)
    return plaintext, token_hash


def hash_refresh_token(token: str) -> str:
    """Hash a refresh token with SHA-256."""
    return hashlib.sha256(token.encode()).hexdigest()
