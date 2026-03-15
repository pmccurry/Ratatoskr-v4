"""Signal module domain errors."""

from app.common.errors import DomainError


class SignalNotFoundError(DomainError):
    def __init__(self, signal_id: str = ""):
        super().__init__(
            code="SIGNAL_NOT_FOUND",
            message=f"Signal not found: {signal_id}" if signal_id else "Signal not found",
        )


class SignalValidationError(DomainError):
    def __init__(self, message: str = "Signal validation failed", details: dict | None = None):
        super().__init__(
            code="SIGNAL_VALIDATION_FAILED",
            message=message,
            details=details,
        )


class SignalTransitionError(DomainError):
    def __init__(self, message: str = "Invalid signal transition", details: dict | None = None):
        super().__init__(
            code="SIGNAL_INVALID_TRANSITION",
            message=message,
            details=details,
        )


class SignalDuplicateError(DomainError):
    def __init__(self, message: str = "Duplicate signal", details: dict | None = None):
        super().__init__(
            code="SIGNAL_DUPLICATE",
            message=message,
            details=details,
        )


class SignalExpiredError(DomainError):
    def __init__(self, signal_id: str = ""):
        super().__init__(
            code="SIGNAL_EXPIRED",
            message=f"Signal expired: {signal_id}" if signal_id else "Signal expired",
        )
