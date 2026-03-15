"""Auth module domain errors."""

from app.common.errors import DomainError


class InvalidCredentialsError(DomainError):
    def __init__(self):
        super().__init__(
            code="AUTH_INVALID_CREDENTIALS",
            message="Invalid credentials",
        )


class AccountLockedError(DomainError):
    def __init__(self, locked_until: str | None = None):
        super().__init__(
            code="AUTH_ACCOUNT_LOCKED",
            message="Account is locked due to too many failed login attempts",
            details={"locked_until": locked_until} if locked_until else {},
        )


class AccountSuspendedError(DomainError):
    def __init__(self):
        super().__init__(
            code="AUTH_ACCOUNT_SUSPENDED",
            message="Account is suspended",
        )


class TokenExpiredError(DomainError):
    def __init__(self):
        super().__init__(
            code="AUTH_TOKEN_EXPIRED",
            message="Access token has expired",
        )


class TokenInvalidError(DomainError):
    def __init__(self):
        super().__init__(
            code="AUTH_TOKEN_INVALID",
            message="Invalid or revoked token",
        )


class InsufficientPermissionsError(DomainError):
    def __init__(self):
        super().__init__(
            code="AUTH_INSUFFICIENT_PERMISSIONS",
            message="Admin access required",
        )


class UserNotFoundError(DomainError):
    def __init__(self, user_id: str | None = None):
        super().__init__(
            code="AUTH_USER_NOT_FOUND",
            message="User not found",
            details={"user_id": user_id} if user_id else {},
        )


class UserAlreadyExistsError(DomainError):
    def __init__(self, field: str, value: str):
        super().__init__(
            code="AUTH_USER_ALREADY_EXISTS",
            message=f"User with {field} '{value}' already exists",
            details={"field": field, "value": value},
        )


class PasswordTooShortError(DomainError):
    def __init__(self, min_length: int):
        super().__init__(
            code="AUTH_PASSWORD_TOO_SHORT",
            message=f"Password must be at least {min_length} characters",
            details={"min_length": min_length},
        )
