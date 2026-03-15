"""OANDA real-time pricing stream.

OANDA uses HTTP chunked transfer, not true WebSocket.
Ticks are accumulated into 1-minute bars at minute boundaries.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from decimal import Decimal

import httpx

from app.market_data.config import get_market_data_config
from app.market_data.streams.base import BrokerWebSocket

logger = logging.getLogger(__name__)


class OandaWebSocket(BrokerWebSocket):
    """OANDA real-time pricing stream.

    OANDA streams pricing via HTTP chunked transfer, not WebSocket.
    URL: {stream_url}/v3/accounts/{account_id}/pricing/stream
    Params: instruments=EUR_USD,GBP_USD,...
    Auth: Bearer token header

    Ticks are accumulated into 1m bars at minute boundaries using mid prices.
    """

    def __init__(self):
        cfg = get_market_data_config()
        self._stream_url = cfg.oanda_stream_url.rstrip("/")
        self._account_id = cfg.oanda_account_id
        self._access_token = cfg.oanda_access_token
        self._client: httpx.AsyncClient | None = None
        self._response = None
        self._connected = False
        self._symbols: list[str] = []
        # Tick accumulation: {symbol: {minute_key, open, high, low, close}}
        self._current_bars: dict[str, dict] = {}
        self._bar_buffer: asyncio.Queue = asyncio.Queue()

    async def connect(self) -> None:
        """Open the HTTP streaming connection."""
        if not self._symbols:
            logger.warning("OANDA stream: no symbols to subscribe, skipping connect")
            return

        self._client = httpx.AsyncClient(timeout=None)
        url = f"{self._stream_url}/v3/accounts/{self._account_id}/pricing/stream"
        params = {"instruments": ",".join(self._symbols)}
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }

        self._response = await self._client.send(
            self._client.build_request("GET", url, params=params, headers=headers),
            stream=True,
        )

        if self._response.status_code != 200:
            body = await self._response.aread()
            raise ConnectionError(
                f"OANDA stream connect failed: HTTP {self._response.status_code} — {body[:200]}"
            )

        self._connected = True
        logger.info("OANDA pricing stream connected (%d instruments)", len(self._symbols))

    async def disconnect(self) -> None:
        """Close the streaming connection."""
        self._connected = False
        if self._response:
            await self._response.aclose()
            self._response = None
        if self._client:
            await self._client.aclose()
            self._client = None

        # Flush any in-progress bars
        for symbol, bar_state in self._current_bars.items():
            if bar_state.get("open") is not None:
                self._bar_buffer.put_nowait(self._emit_bar(symbol, bar_state))
        self._current_bars.clear()
        logger.info("OANDA pricing stream disconnected")

    async def subscribe(self, symbols: list[str]) -> None:
        """Add symbols to the stream.

        OANDA requires reconnecting with a new instruments list.
        """
        new_symbols = [s for s in symbols if s not in self._symbols]
        if not new_symbols:
            return

        was_connected = self._connected
        if was_connected:
            await self.disconnect()

        self._symbols.extend(new_symbols)

        if was_connected or self._symbols:
            await self.connect()

        logger.info("OANDA stream subscribed to %d new symbols (total: %d)", len(new_symbols), len(self._symbols))

    async def unsubscribe(self, symbols: list[str]) -> None:
        """Remove symbols from the stream.

        Requires reconnecting with updated instruments list.
        """
        remove = [s for s in symbols if s in self._symbols]
        if not remove:
            return

        was_connected = self._connected
        if was_connected:
            await self.disconnect()

        for s in remove:
            self._symbols.remove(s)
            self._current_bars.pop(s, None)

        if was_connected and self._symbols:
            await self.connect()

        logger.info("OANDA stream unsubscribed from %d symbols (total: %d)", len(remove), len(self._symbols))

    async def receive(self) -> dict | None:
        """Receive the next completed 1m bar.

        Reads from the HTTP stream, accumulates ticks, and emits bars
        at minute boundaries.
        """
        # First check if we have buffered completed bars
        if not self._bar_buffer.empty():
            return self._bar_buffer.get_nowait()

        if not self._response or not self._connected:
            return None

        try:
            async for line in self._response.aiter_lines():
                if not line.strip():
                    continue

                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue

                msg_type = data.get("type")

                if msg_type == "HEARTBEAT":
                    # Use heartbeats for liveness — just continue
                    continue

                if msg_type == "PRICE":
                    bar = self._process_tick(data)
                    if bar is not None:
                        return bar

                    # Also check buffer for any bars completed by this tick
                    if not self._bar_buffer.empty():
                        return self._bar_buffer.get_nowait()

        except (httpx.ReadError, httpx.StreamClosed, httpx.RemoteProtocolError):
            self._connected = False
            logger.warning("OANDA pricing stream disconnected")
            return None
        except Exception as e:
            self._connected = False
            logger.error("OANDA stream receive error: %s", e)
            return None

        # Stream ended
        self._connected = False
        return None

    def _process_tick(self, data: dict) -> dict | None:
        """Process a PRICE tick and accumulate into 1m bars.

        Returns a completed bar dict if a minute boundary was crossed,
        or None if still accumulating.
        """
        instrument = data.get("instrument", "")
        if instrument not in self._symbols:
            return None

        # Extract bid/ask and compute mid price
        bids = data.get("bids", [])
        asks = data.get("asks", [])
        if not bids or not asks:
            return None

        bid = Decimal(str(bids[0].get("price", "0")))
        ask = Decimal(str(asks[0].get("price", "0")))
        mid = (bid + ask) / Decimal("2")

        # Get timestamp and determine minute key
        ts_str = data.get("time", "")
        try:
            tick_ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None

        minute_key = tick_ts.replace(second=0, microsecond=0)

        current = self._current_bars.get(instrument)

        completed_bar = None

        if current is not None and current["minute_key"] != minute_key:
            # Minute boundary crossed — emit the completed bar
            completed_bar = self._emit_bar(instrument, current)

        if current is None or current["minute_key"] != minute_key:
            # Start a new bar
            self._current_bars[instrument] = {
                "minute_key": minute_key,
                "open": mid,
                "high": mid,
                "low": mid,
                "close": mid,
            }
        else:
            # Update current bar
            current["high"] = max(current["high"], mid)
            current["low"] = min(current["low"], mid)
            current["close"] = mid

        return completed_bar

    def _emit_bar(self, symbol: str, bar_state: dict) -> dict:
        """Convert accumulated tick state into a bar dict."""
        return {
            "symbol": symbol,
            "timeframe": "1m",
            "ts": bar_state["minute_key"],
            "open": bar_state["open"],
            "high": bar_state["high"],
            "low": bar_state["low"],
            "close": bar_state["close"],
            "volume": Decimal("0"),  # OANDA ticks don't have volume
            "market": "forex",
        }

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def subscribed_symbols(self) -> list[str]:
        return list(self._symbols)
