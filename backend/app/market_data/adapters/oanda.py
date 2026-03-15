"""OANDA broker adapter — forex.

Implements REST API calls for instrument listing and historical candles.
WebSocket operations (TASK-007) remain as NotImplementedError.
"""

import asyncio
import logging
from datetime import date, datetime, timezone
from decimal import Decimal

import httpx

from app.market_data.adapters.base import BrokerAdapter
from app.market_data.backfill.rate_limiter import RateLimiter
from app.market_data.config import get_market_data_config
from app.market_data.errors import MarketDataConnectionError

logger = logging.getLogger(__name__)

# OANDA granularity mapping
_TIMEFRAME_MAP = {
    "1m": "M1",
    "5m": "M5",
    "15m": "M15",
    "1h": "H1",
    "4h": "H4",
    "1d": "D",
}


class OandaAdapter(BrokerAdapter):
    """OANDA implementation of the broker adapter interface."""

    def __init__(self, rate_limiter: RateLimiter | None = None):
        cfg = get_market_data_config()
        self._access_token = cfg.oanda_access_token
        self._account_id = cfg.oanda_account_id
        self._base_url = cfg.oanda_base_url.rstrip("/")
        self._rate_limiter = rate_limiter or RateLimiter(max_requests_per_minute=5000)
        self._headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }

    @property
    def broker_name(self) -> str:
        return "oanda"

    @property
    def supported_markets(self) -> list[str]:
        return ["forex"]

    async def _request(
        self, method: str, url: str, params: dict | None = None, max_retries: int = 3
    ) -> dict | list:
        """Make an authenticated HTTP request with rate limiting and retry."""
        await self._rate_limiter.acquire()

        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.request(
                        method, url, headers=self._headers, params=params
                    )

                if resp.status_code == 429:
                    wait = min(2 ** attempt * 2, 30)
                    logger.warning(
                        "OANDA rate limited (429) on %s, retrying in %ds (attempt %d/%d)",
                        url, wait, attempt + 1, max_retries,
                    )
                    await asyncio.sleep(wait)
                    await self._rate_limiter.acquire()
                    continue

                if 400 <= resp.status_code < 500:
                    logger.error("OANDA client error %d on %s: %s", resp.status_code, url, resp.text)
                    raise MarketDataConnectionError(
                        "oanda",
                        f"HTTP {resp.status_code} on {url}: {resp.text[:200]}",
                    )

                if resp.status_code >= 500:
                    logger.error("OANDA server error %d on %s", resp.status_code, url)
                    raise MarketDataConnectionError(
                        "oanda", f"HTTP {resp.status_code} on {url}"
                    )

                return resp.json()

            except httpx.TimeoutException:
                logger.error("OANDA timeout on %s (attempt %d/%d)", url, attempt + 1, max_retries)
                if attempt == max_retries - 1:
                    raise MarketDataConnectionError("oanda", f"Timeout on {url}")
            except (httpx.ConnectError, httpx.ReadError) as e:
                logger.error("OANDA connection error on %s: %s", url, e)
                if attempt == max_retries - 1:
                    raise MarketDataConnectionError("oanda", f"Connection error on {url}: {e}")

        raise MarketDataConnectionError("oanda", f"Max retries exceeded on {url}")

    async def list_available_symbols(self) -> list[dict]:
        """Fetch all tradable instruments from OANDA."""
        url = f"{self._base_url}/v3/accounts/{self._account_id}/instruments"
        data = await self._request("GET", url)

        instruments = data.get("instruments", [])
        symbols = []
        for inst in instruments:
            name = inst.get("name", "")
            display_name = inst.get("displayName", name)
            # OANDA uses "EUR_USD" format — split to get base/quote
            parts = name.split("_")
            base = parts[0] if len(parts) == 2 else None
            quote = parts[1] if len(parts) == 2 else None

            symbols.append({
                "symbol": name,
                "name": display_name,
                "market": "forex",
                "exchange": None,
                "base_asset": base,
                "quote_asset": quote,
                "broker": "oanda",
                "status": "active",
                "options_enabled": False,
            })

        logger.info("OANDA: fetched %d instruments", len(symbols))
        return symbols

    async def fetch_historical_bars(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
        limit: int | None = None,
    ) -> list[dict]:
        """Fetch historical candles from OANDA, converting mid prices to OHLCV.

        OANDA caps responses at 5,000 candles. Paginates using 'from' + 'count'
        (not 'to') to stay within the limit.
        """
        granularity = _TIMEFRAME_MAP.get(timeframe)
        if not granularity:
            raise ValueError(f"Unsupported timeframe: {timeframe}")

        _MAX_CANDLES = 5000
        all_bars = []
        current_start = start

        while current_start < end:
            # Use 'from' + 'count' (not 'to') to respect OANDA's 5000 candle limit.
            # OANDA returns an error if both 'to' and 'count' are set when the range
            # exceeds 5000 candles.
            params = {
                "granularity": granularity,
                "from": current_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "count": _MAX_CANDLES,
                "price": "M",  # mid prices
            }

            url = f"{self._base_url}/v3/instruments/{symbol}/candles"
            data = await self._request("GET", url, params=params)

            candles = data.get("candles", [])
            if not candles:
                break

            past_end = False
            for candle in candles:
                if not candle.get("complete", True):
                    continue  # skip incomplete candles

                mid = candle.get("mid", {})
                ts_str = candle.get("time", "")
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))

                if ts >= end:
                    past_end = True
                    break  # Don't include candles past the requested end

                all_bars.append({
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "ts": ts,
                    "open": Decimal(str(mid.get("o", 0))),
                    "high": Decimal(str(mid.get("h", 0))),
                    "low": Decimal(str(mid.get("l", 0))),
                    "close": Decimal(str(mid.get("c", 0))),
                    "volume": Decimal(str(candle.get("volume", 0))),
                })

            if past_end:
                break

            # Move start forward past the last candle we received
            last_ts = datetime.fromisoformat(candles[-1]["time"].replace("Z", "+00:00"))
            if last_ts <= current_start:
                break  # no progress, avoid infinite loop
            current_start = last_ts

            # Fewer than max means we've reached the available data
            if len(candles) < _MAX_CANDLES:
                break

            if limit and len(all_bars) >= limit:
                break

        if limit:
            all_bars = all_bars[:limit]

        return all_bars

    async def fetch_option_chain(self, underlying_symbol: str) -> dict | None:
        """OANDA does not support options."""
        return None

    async def fetch_dividends(
        self,
        symbols: list[str],
        start_date: date,
        end_date: date,
    ) -> list[dict]:
        """Forex pairs don't have dividends."""
        return []

    # === WebSocket operations ===

    async def subscribe_bars(self, symbols: list[str]) -> None:
        """Delegate to the WebSocket manager."""
        from app.market_data.startup import get_ws_manager

        mgr = get_ws_manager()
        if mgr is None:
            raise RuntimeError("WebSocket manager not initialized")
        await mgr.subscribe("oanda", symbols)

    async def unsubscribe_bars(self, symbols: list[str]) -> None:
        """Delegate to the WebSocket manager."""
        from app.market_data.startup import get_ws_manager

        mgr = get_ws_manager()
        if mgr is None:
            raise RuntimeError("WebSocket manager not initialized")
        await mgr.unsubscribe("oanda", symbols)

    async def get_connection_health(self) -> dict:
        """Return health status from the WebSocket manager for OANDA."""
        from app.market_data.startup import get_ws_manager

        mgr = get_ws_manager()
        if mgr is None:
            return {"broker": "oanda", "status": "disconnected"}
        health = mgr.get_health()
        return health.get("oanda", {"broker": "oanda", "status": "disconnected"})
