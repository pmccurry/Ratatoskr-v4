"""Password hashing and verification using bcrypt."""

import bcrypt

from app.auth.errors import PasswordTooShortError
from app.common.config import get_settings


def validate_password_length(password: str) -> None:
    """Validate password meets minimum length. Raises PasswordTooShortError."""
    settings = get_settings()
    if len(password) < settings.auth_min_password_length:
        raise PasswordTooShortError(settings.auth_min_password_length)


def hash_password(password: str) -> str:
    """Hash password using bcrypt with configured cost factor."""
    validate_password_length(password)
    settings = get_settings()
    salt = bcrypt.gensalt(rounds=settings.auth_bcrypt_cost_factor)
    return bcrypt.hashpw(password.encode(), salt).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a bcrypt hash."""
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())
