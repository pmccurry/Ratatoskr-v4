"""Abstract base for broker-specific WebSocket connections."""

from abc import ABC, abstractmethod


class BrokerWebSocket(ABC):
    """Abstract WebSocket connection to a broker.

    Each broker implements this interface to handle its specific
    connection protocol (true WebSocket for Alpaca, HTTP streaming
    for OANDA).
    """

    @abstractmethod
    async def connect(self) -> None:
        """Establish the connection and authenticate."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Close the connection cleanly."""

    @abstractmethod
    async def subscribe(self, symbols: list[str]) -> None:
        """Subscribe to bar updates for symbols."""

    @abstractmethod
    async def unsubscribe(self, symbols: list[str]) -> None:
        """Unsubscribe from symbols."""

    @abstractmethod
    async def receive(self) -> dict | None:
        """Receive the next bar message.

        Returns a parsed bar dict with keys:
          symbol, timeframe, ts, open, high, low, close, volume, market
        Or None on disconnection.
        """

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Whether the connection is currently alive."""

    @property
    @abstractmethod
    def subscribed_symbols(self) -> list[str]:
        """Currently subscribed symbols."""
