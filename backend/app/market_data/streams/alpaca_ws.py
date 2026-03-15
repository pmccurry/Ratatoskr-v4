"""Alpaca real-time bar streaming via WebSocket."""

import asyncio
import json
import logging
from datetime import datetime, timezone
from decimal import Decimal

import websockets

from app.market_data.config import get_market_data_config
from app.market_data.streams.base import BrokerWebSocket

logger = logging.getLogger(__name__)


class AlpacaWebSocket(BrokerWebSocket):
    """Alpaca real-time bar streaming via WebSocket.

    URL: wss://stream.data.alpaca.markets/v2/sip
    Auth: send {"action": "auth", "key": api_key, "secret": api_secret}
    Subscribe: send {"action": "subscribe", "bars": [symbols]}
    Messages: {"T": "b", "S": symbol, "o": open, "h": high, "l": low,
               "c": close, "v": volume, "t": timestamp}
    """

    def __init__(self):
        cfg = get_market_data_config()
        self._ws_url = cfg.alpaca_data_ws_url
        self._api_key = cfg.alpaca_api_key
        self._api_secret = cfg.alpaca_api_secret
        self._ws = None
        self._connected = False
        self._symbols: list[str] = []

    async def connect(self) -> None:
        """Connect and authenticate to the Alpaca WebSocket."""
        self._ws = await websockets.connect(self._ws_url)

        # Wait for welcome message
        welcome = await self._ws.recv()
        welcome_data = json.loads(welcome)
        logger.debug("Alpaca WS welcome: %s", welcome_data)

        # Authenticate
        auth_msg = json.dumps({
            "action": "auth",
            "key": self._api_key,
            "secret": self._api_secret,
        })
        await self._ws.send(auth_msg)

        auth_resp = await self._ws.recv()
        auth_data = json.loads(auth_resp)
        logger.debug("Alpaca WS auth response: %s", auth_data)

        # Check auth success — response is a list, first item has T="success"
        if isinstance(auth_data, list) and auth_data:
            if auth_data[0].get("T") == "error":
                raise ConnectionError(f"Alpaca WS auth failed: {auth_data[0]}")

        self._connected = True
        logger.info("Alpaca WebSocket connected and authenticated")

    async def disconnect(self) -> None:
        """Close the WebSocket connection."""
        self._connected = False
        if self._ws:
            await self._ws.close()
            self._ws = None
        self._symbols = []
        logger.info("Alpaca WebSocket disconnected")

    async def subscribe(self, symbols: list[str]) -> None:
        """Subscribe to bar updates for symbols."""
        if not self._ws or not self._connected:
            raise ConnectionError("Not connected to Alpaca WebSocket")

        new_symbols = [s for s in symbols if s not in self._symbols]
        if not new_symbols:
            return

        msg = json.dumps({"action": "subscribe", "bars": new_symbols})
        await self._ws.send(msg)

        # Wait for subscription confirmation
        resp = await self._ws.recv()
        resp_data = json.loads(resp)
        logger.debug("Alpaca WS subscribe response: %s", resp_data)

        self._symbols.extend(new_symbols)
        logger.info("Alpaca WS subscribed to %d symbols (total: %d)", len(new_symbols), len(self._symbols))

    async def unsubscribe(self, symbols: list[str]) -> None:
        """Unsubscribe from bar updates for symbols."""
        if not self._ws or not self._connected:
            return

        remove = [s for s in symbols if s in self._symbols]
        if not remove:
            return

        msg = json.dumps({"action": "unsubscribe", "bars": remove})
        await self._ws.send(msg)

        resp = await self._ws.recv()
        logger.debug("Alpaca WS unsubscribe response: %s", json.loads(resp))

        for s in remove:
            self._symbols.remove(s)
        logger.info("Alpaca WS unsubscribed from %d symbols (total: %d)", len(remove), len(self._symbols))

    async def receive(self) -> dict | None:
        """Receive the next bar message.

        Returns parsed bar dict or None on real disconnect.
        Loops internally over non-bar messages (heartbeats, status updates)
        so the caller doesn't trigger unnecessary reconnection.
        """
        while True:
            if not self._ws or not self._connected:
                return None

            try:
                raw = await self._ws.recv()
            except (websockets.ConnectionClosed, websockets.ConnectionClosedError):
                self._connected = False
                logger.warning("Alpaca WebSocket connection closed")
                return None
            except Exception as e:
                self._connected = False
                logger.error("Alpaca WebSocket receive error: %s", e)
                return None

            messages = json.loads(raw)
            if not isinstance(messages, list):
                messages = [messages]

            for msg in messages:
                msg_type = msg.get("T")

                if msg_type == "b":
                    ts_str = msg.get("t", "")
                    ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))

                    return {
                        "symbol": msg["S"],
                        "timeframe": "1m",
                        "ts": ts,
                        "open": Decimal(str(msg["o"])),
                        "high": Decimal(str(msg["h"])),
                        "low": Decimal(str(msg["l"])),
                        "close": Decimal(str(msg["c"])),
                        "volume": Decimal(str(msg["v"])),
                        "market": "equities",
                    }

                if msg_type == "error":
                    logger.error("Alpaca WS error: %s", msg)

            # No bar in this batch — loop to wait for next message
            # (don't return None, which would trigger reconnection)

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def subscribed_symbols(self) -> list[str]:
        return list(self._symbols)
