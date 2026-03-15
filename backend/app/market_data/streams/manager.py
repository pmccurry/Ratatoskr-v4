"""WebSocket manager — central coordinator for all broker connections."""

import asyncio
import logging
from datetime import datetime, timezone

from app.market_data.config import MarketDataConfig
from app.market_data.streams.alpaca_ws import AlpacaWebSocket
from app.market_data.streams.base import BrokerWebSocket
from app.market_data.streams.health import ConnectionHealth
from app.market_data.streams.oanda_ws import OandaWebSocket

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manages WebSocket connections to all brokers.

    Responsibilities:
    - Start/stop connections per broker
    - Track connection state
    - Route incoming bars to the processing queue
    - Handle reconnection with exponential backoff
    - Trigger gap backfill after reconnection
    - Expose health status
    """

    def __init__(self, bar_queue: asyncio.Queue, config: MarketDataConfig):
        self._connections: dict[str, BrokerWebSocket] = {}
        self._bar_queue = bar_queue
        self._config = config
        self._health: dict[str, ConnectionHealth] = {}
        self._receive_tasks: dict[str, asyncio.Task] = {}
        self._running = False

    async def start(self, broker: str, symbols: list[str]) -> None:
        """Start streaming bars for a broker's symbols.

        1. Create the appropriate BrokerWebSocket
        2. Connect and subscribe to symbols
        3. Start the receive loop (as an asyncio task)
        4. Update health status
        """
        if not symbols:
            logger.info("No symbols for %s, skipping WebSocket start", broker)
            return

        self._running = True
        ws = self._create_connection(broker)
        self._connections[broker] = ws
        self._health[broker] = ConnectionHealth(broker=broker)

        try:
            if broker == "oanda":
                # OANDA needs symbols set before connect
                await ws.subscribe(symbols)
            else:
                await ws.connect()
                await ws.subscribe(symbols)

            health = self._health[broker]
            health.status = "connected"
            health.connected_since = datetime.now(timezone.utc)
            health.subscribed_symbols = len(ws.subscribed_symbols)
            health.reconnect_attempts = 0

            # Start receive loop
            self._receive_tasks[broker] = asyncio.create_task(
                self._receive_loop(broker)
            )

            logger.info(
                "WebSocket started for %s — %d symbols", broker, len(symbols)
            )
        except Exception as e:
            logger.error("Failed to start WebSocket for %s: %s", broker, e)
            self._health[broker].status = "disconnected"
            raise

    async def stop(self, broker: str | None = None) -> None:
        """Stop streaming. If broker=None, stop all."""
        brokers = [broker] if broker else list(self._connections.keys())
        self._running = False

        for b in brokers:
            # Cancel receive task
            task = self._receive_tasks.pop(b, None)
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

            # Disconnect
            ws = self._connections.pop(b, None)
            if ws:
                await ws.disconnect()

            if b in self._health:
                self._health[b].status = "disconnected"
                self._health[b].last_disconnect_at = datetime.now(timezone.utc)

            logger.info("WebSocket stopped for %s", b)

    async def subscribe(self, broker: str, symbols: list[str]) -> None:
        """Add symbols to an existing connection."""
        ws = self._connections.get(broker)
        if not ws:
            logger.warning("Cannot subscribe: no connection for %s", broker)
            return

        await ws.subscribe(symbols)
        if broker in self._health:
            self._health[broker].subscribed_symbols = len(ws.subscribed_symbols)

    async def unsubscribe(self, broker: str, symbols: list[str]) -> None:
        """Remove symbols from an existing connection."""
        ws = self._connections.get(broker)
        if not ws:
            return

        await ws.unsubscribe(symbols)
        if broker in self._health:
            self._health[broker].subscribed_symbols = len(ws.subscribed_symbols)

    def get_health(self) -> dict:
        """Return health status for all connections."""
        return {
            broker: health.to_dict()
            for broker, health in self._health.items()
        }

    async def _receive_loop(self, broker: str) -> None:
        """Receive bars from WebSocket, push to queue.

        Runs as an asyncio task. On disconnection:
        1. Record disconnect time
        2. Update health status
        3. Start reconnection loop
        """
        ws = self._connections.get(broker)
        if not ws:
            return

        while self._running:
            try:
                bar = await ws.receive()

                if bar is None:
                    # Connection lost
                    disconnect_time = datetime.now(timezone.utc)
                    health = self._health.get(broker)
                    if health:
                        health.status = "disconnected"
                        health.last_disconnect_at = disconnect_time

                    logger.warning("WebSocket disconnected for %s, starting reconnection", broker)

                    if self._running:
                        await self._reconnect(broker, disconnect_time)
                    break

                # Push bar to processing queue
                try:
                    self._bar_queue.put_nowait(bar)
                except asyncio.QueueFull:
                    logger.warning("Bar queue full, dropping bar for %s", bar.get("symbol"))

                # Update health
                health = self._health.get(broker)
                if health:
                    health.last_message_at = datetime.now(timezone.utc)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in receive loop for %s: %s", broker, e)
                if self._running:
                    await self._reconnect(broker, datetime.now(timezone.utc))
                break

    async def _reconnect(self, broker: str, disconnect_time: datetime) -> None:
        """Reconnect with exponential backoff.

        After successful reconnection:
        1. Re-subscribe to all symbols
        2. Trigger gap backfill for the disconnection period
        3. Update health status
        """
        health = self._health.get(broker)
        if health:
            health.status = "reconnecting"

        # Remember symbols to re-subscribe
        old_ws = self._connections.get(broker)
        symbols = old_ws.subscribed_symbols if old_ws else []

        delay = self._config.ws_reconnect_initial_delay
        attempt = 0

        while self._running:
            attempt += 1
            if health:
                health.reconnect_attempts = attempt

            logger.info(
                "Reconnecting %s (attempt %d, delay %ds)", broker, attempt, delay
            )

            try:
                await asyncio.sleep(delay)
            except asyncio.CancelledError:
                return

            try:
                # Create new connection
                ws = self._create_connection(broker)
                self._connections[broker] = ws

                if broker == "oanda" and symbols:
                    await ws.subscribe(symbols)
                else:
                    await ws.connect()
                    if symbols:
                        await ws.subscribe(symbols)

                # Success
                reconnect_time = datetime.now(timezone.utc)
                if health:
                    health.status = "connected"
                    health.connected_since = reconnect_time
                    health.subscribed_symbols = len(ws.subscribed_symbols)

                logger.info(
                    "Reconnected %s after %d attempts, triggering gap backfill",
                    broker, attempt,
                )

                # Trigger gap backfill
                asyncio.create_task(
                    self._gap_backfill(broker, symbols, disconnect_time, reconnect_time)
                )

                # Restart receive loop
                self._receive_tasks[broker] = asyncio.create_task(
                    self._receive_loop(broker)
                )
                return

            except Exception as e:
                logger.warning("Reconnect attempt %d for %s failed: %s", attempt, broker, e)

            # Exponential backoff
            delay = min(
                delay * self._config.ws_reconnect_backoff_multiplier,
                self._config.ws_reconnect_max_delay,
            )

    async def _gap_backfill(
        self,
        broker: str,
        symbols: list[str],
        disconnect_time: datetime,
        reconnect_time: datetime,
    ) -> None:
        """Trigger gap backfill for the disconnection period."""
        from app.common.database import get_session_factory
        from app.market_data.backfill.runner import backfill_gap

        factory = get_session_factory()
        async with factory() as db:
            try:
                total = 0
                for symbol in symbols:
                    count = await backfill_gap(
                        db, symbol, "1m", disconnect_time, reconnect_time
                    )
                    total += count
                await db.commit()
                logger.info(
                    "Gap backfill complete for %s: %d bars across %d symbols",
                    broker, total, len(symbols),
                )
            except Exception as e:
                await db.rollback()
                logger.error("Gap backfill failed for %s: %s", broker, e)

    def _create_connection(self, broker: str) -> BrokerWebSocket:
        """Create the appropriate BrokerWebSocket for a broker."""
        if broker == "alpaca":
            return AlpacaWebSocket()
        elif broker == "oanda":
            return OandaWebSocket()
        raise ValueError(f"Unknown broker: {broker}")
