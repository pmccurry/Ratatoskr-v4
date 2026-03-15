"""Portfolio domain errors."""

from app.common.errors import DomainError


class PositionNotFoundError(DomainError):
    def __init__(self, position_id: str = ""):
        super().__init__(
            code="PORTFOLIO_POSITION_NOT_FOUND",
            message=f"Position not found: {position_id}" if position_id else "Position not found",
        )


class InsufficientCashError(DomainError):
    def __init__(self, required: str = "", available: str = ""):
        super().__init__(
            code="PORTFOLIO_INSUFFICIENT_CASH",
            message=f"Insufficient cash: required={required}, available={available}",
            details={"required": required, "available": available},
        )


class InvalidFillError(DomainError):
    def __init__(self, message: str = "Invalid fill"):
        super().__init__(
            code="PORTFOLIO_INVALID_FILL",
            message=message,
        )


class PortfolioStateError(DomainError):
    def __init__(self, message: str = "Portfolio state error"):
        super().__init__(
            code="PORTFOLIO_STATE_ERROR",
            message=message,
        )
