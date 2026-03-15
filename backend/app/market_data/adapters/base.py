"""Abstract broker adapter interface.

Every broker (Alpaca, OANDA) implements this interface.
The market data service routes to the correct adapter based
on the symbol's market (equities -> Alpaca, forex -> OANDA).
"""

from abc import ABC, abstractmethod
from datetime import date, datetime


class BrokerAdapter(ABC):
    """Abstract interface for broker data adapters."""

    @property
    @abstractmethod
    def broker_name(self) -> str:
        """Return the broker identifier (e.g., 'alpaca', 'oanda')."""

    @property
    @abstractmethod
    def supported_markets(self) -> list[str]:
        """Return list of markets this adapter handles (e.g., ['equities', 'forex'])."""

    @abstractmethod
    async def list_available_symbols(self) -> list[dict]:
        """Fetch all tradable symbols from the broker.

        Returns a list of dicts with at minimum:
          symbol, name, market, exchange, base_asset, quote_asset,
          status, options_enabled
        """

    @abstractmethod
    async def fetch_historical_bars(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
        limit: int | None = None,
    ) -> list[dict]:
        """Fetch historical OHLCV bars for a symbol.

        Returns a list of dicts with:
          symbol, timeframe, ts, open, high, low, close, volume
        All prices as Decimal. ts as timezone-aware UTC datetime.
        """

    @abstractmethod
    async def subscribe_bars(self, symbols: list[str]) -> None:
        """Subscribe to real-time bar streaming for given symbols.

        Implementation connects to broker WebSocket and begins
        receiving bars. Received bars are pushed to the provided
        callback or queue.
        """

    @abstractmethod
    async def unsubscribe_bars(self, symbols: list[str]) -> None:
        """Unsubscribe from bar streaming for given symbols."""

    @abstractmethod
    async def get_connection_health(self) -> dict:
        """Return current connection health status.

        Returns dict with at minimum:
          status ('connected' | 'disconnected' | 'reconnecting'),
          connected_since (datetime | None),
          last_message_at (datetime | None),
          subscribed_symbols (int)
        """

    @abstractmethod
    async def fetch_option_chain(self, underlying_symbol: str) -> dict | None:
        """Fetch option chain snapshot for an underlying symbol.

        Returns dict with contract data including Greeks, or None
        if options are not supported by this broker.
        """

    @abstractmethod
    async def fetch_dividends(
        self,
        symbols: list[str],
        start_date: date,
        end_date: date,
    ) -> list[dict]:
        """Fetch dividend announcements for symbols in date range.

        Returns list of dicts matching DividendAnnouncement fields.
        """
