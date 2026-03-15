"""Market data module domain errors."""

from app.common.errors import DomainError


class SymbolNotFoundError(DomainError):
    """Raised when a market symbol is not found."""

    def __init__(self, symbol: str):
        super().__init__(
            code="MARKET_DATA_SYMBOL_NOT_FOUND",
            message=f"Symbol '{symbol}' not found",
            details={"symbol": symbol},
        )


class MarketDataStaleError(DomainError):
    """Raised when market data is stale and unreliable."""

    def __init__(self, symbol: str | None = None):
        details = {}
        if symbol:
            details["symbol"] = symbol
        super().__init__(
            code="MARKET_DATA_STALE",
            message="Market data is stale",
            details=details,
        )


class BackfillFailedError(DomainError):
    """Raised when a backfill job fails."""

    def __init__(self, symbol: str, reason: str):
        super().__init__(
            code="MARKET_DATA_BACKFILL_FAILED",
            message=f"Backfill failed for '{symbol}': {reason}",
            details={"symbol": symbol, "reason": reason},
        )


class MarketDataConnectionError(DomainError):
    """Raised when a broker connection fails."""

    def __init__(self, broker: str, reason: str):
        super().__init__(
            code="MARKET_DATA_CONNECTION_ERROR",
            message=f"Connection error for broker '{broker}': {reason}",
            details={"broker": broker, "reason": reason},
        )
