"""Domain error base class, error-to-status mapping, and exception handlers."""

import logging

from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class DomainError(Exception):
    """Base class for all domain-specific errors."""

    def __init__(self, code: str, message: str, details: dict | None = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)


# Error code to HTTP status mapping
_ERROR_STATUS_MAP: dict[str, int] = {
    # Auth
    "AUTH_INVALID_CREDENTIALS": 401,
    "AUTH_TOKEN_EXPIRED": 401,
    "AUTH_TOKEN_INVALID": 401,
    "AUTH_INSUFFICIENT_PERMISSIONS": 403,
    "AUTH_ACCOUNT_SUSPENDED": 403,
    "AUTH_ACCOUNT_LOCKED": 423,
    "AUTH_USER_NOT_FOUND": 404,
    "AUTH_USER_ALREADY_EXISTS": 409,
    "AUTH_PASSWORD_TOO_SHORT": 400,
    # Strategy
    "STRATEGY_NOT_FOUND": 404,
    "STRATEGY_VALIDATION_FAILED": 422,
    "STRATEGY_NOT_ENABLED": 422,
    "STRATEGY_CONFIG_INVALID": 422,
    "STRATEGY_ALREADY_EXISTS": 409,
    "STRATEGY_INVALID_CONFIG": 400,
    "STRATEGY_EVALUATION_ERROR": 500,
    "STRATEGY_FORMULA_PARSE_ERROR": 400,
    "STRATEGY_FORMULA_VALIDATION_ERROR": 400,
    "STRATEGY_INDICATOR_NOT_FOUND": 400,
    "STRATEGY_INVALID_CONDITION": 400,
    # Signal
    "SIGNAL_NOT_FOUND": 404,
    "SIGNAL_VALIDATION_FAILED": 422,
    "SIGNAL_DUPLICATE": 409,
    "SIGNAL_EXPIRED": 422,
    "SIGNAL_INVALID_TRANSITION": 422,
    "SIGNAL_CANNOT_CANCEL": 422,
    # Risk
    "RISK_KILL_SWITCH_ACTIVE": 422,
    "RISK_EXPOSURE_LIMIT": 422,
    "RISK_DRAWDOWN_LIMIT": 422,
    "RISK_DAILY_LOSS_LIMIT": 422,
    "RISK_NO_AVAILABLE_ACCOUNT": 422,
    "RISK_DUPLICATE_ORDER": 409,
    "RISK_MAX_POSITIONS": 422,
    "RISK_EVALUATION_ERROR": 500,
    "RISK_CONFIG_NOT_FOUND": 404,
    "RISK_KILL_SWITCH_ALREADY_ACTIVE": 409,
    "RISK_KILL_SWITCH_NOT_ACTIVE": 409,
    "RISK_DECISION_NOT_FOUND": 404,
    # Paper Trading
    "PAPER_TRADING_INSUFFICIENT_CASH": 422,
    "PAPER_TRADING_BROKER_ERROR": 500,
    "PAPER_TRADING_INVALID_ORDER": 422,
    "PAPER_TRADING_NO_REFERENCE_PRICE": 422,
    "PAPER_TRADING_ORDER_NOT_FOUND": 404,
    "PAPER_TRADING_ORDER_REJECTED": 400,
    "PAPER_TRADING_FILL_NOT_FOUND": 404,
    "PAPER_TRADING_EXECUTION_ERROR": 500,
    "PAPER_TRADING_ORDER_ALREADY_FILLED": 409,
    # Portfolio
    "PORTFOLIO_POSITION_NOT_FOUND": 404,
    "PORTFOLIO_INVALID_OPERATION": 422,
    "PORTFOLIO_NO_OPEN_POSITION": 422,
    "PORTFOLIO_INSUFFICIENT_CASH": 400,
    "PORTFOLIO_INVALID_FILL": 400,
    "PORTFOLIO_STATE_ERROR": 500,
    # Market Data
    "MARKET_DATA_SYMBOL_NOT_FOUND": 404,
    "MARKET_DATA_STALE": 503,
    "MARKET_DATA_BACKFILL_FAILED": 500,
    "MARKET_DATA_CONNECTION_ERROR": 503,
    # Observability
    "OBSERVABILITY_EVENT_NOT_FOUND": 404,
    "OBSERVABILITY_ALERT_RULE_NOT_FOUND": 404,
    "OBSERVABILITY_ALERT_NOT_FOUND": 404,
    # System
    "VALIDATION_ERROR": 400,
    "NOT_FOUND": 404,
    "INTERNAL_ERROR": 500,
}


def map_error_code_to_status(code: str) -> int:
    """Map a domain error code to an HTTP status code."""
    return _ERROR_STATUS_MAP.get(code, 500)


async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    """Handle DomainError exceptions and return structured error responses."""
    status = map_error_code_to_status(exc.code)
    return JSONResponse(
        status_code=status,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            }
        },
    )


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unhandled exceptions. Never expose internals to the client."""
    logger.exception("Unhandled exception")
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An internal error occurred",
                "details": {},
            }
        },
    )
