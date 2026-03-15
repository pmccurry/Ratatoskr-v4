"""Paper trading domain errors."""

from app.common.errors import DomainError


class OrderNotFoundError(DomainError):
    def __init__(self, order_id: str = ""):
        super().__init__(
            code="PAPER_TRADING_ORDER_NOT_FOUND",
            message=f"Paper order not found: {order_id}" if order_id else "Paper order not found",
        )


class OrderRejectedError(DomainError):
    def __init__(self, reason: str = ""):
        super().__init__(
            code="PAPER_TRADING_ORDER_REJECTED",
            message=f"Order rejected: {reason}" if reason else "Order rejected",
        )


class InsufficientCashError(DomainError):
    def __init__(self, required: str = "", available: str = ""):
        super().__init__(
            code="PAPER_TRADING_INSUFFICIENT_CASH",
            message=f"Insufficient cash: required={required}, available={available}",
            details={"required": required, "available": available},
        )


class FillNotFoundError(DomainError):
    def __init__(self, fill_id: str = ""):
        super().__init__(
            code="PAPER_TRADING_FILL_NOT_FOUND",
            message=f"Paper fill not found: {fill_id}" if fill_id else "Paper fill not found",
        )


class ExecutionError(DomainError):
    def __init__(self, message: str = "Execution error"):
        super().__init__(
            code="PAPER_TRADING_EXECUTION_ERROR",
            message=message,
        )


class OrderAlreadyFilledError(DomainError):
    def __init__(self, order_id: str = ""):
        super().__init__(
            code="PAPER_TRADING_ORDER_ALREADY_FILLED",
            message=f"Order already filled: {order_id}" if order_id else "Order already filled",
        )
