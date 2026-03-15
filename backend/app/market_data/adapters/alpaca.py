"""Alpaca broker adapter — equities, options.

Implements REST API calls for symbol listing, historical bars,
option chains, and corporate actions. WebSocket operations (TASK-007)
remain as NotImplementedError.
"""

import asyncio
import logging
from datetime import date, datetime, timezone
from decimal import Decimal

import httpx

from app.market_data.adapters.base import BrokerAdapter
from app.market_data.backfill.rate_limiter import RateLimiter
from app.market_data.config import get_market_data_config
from app.market_data.errors import MarketDataConnectionError, SymbolNotFoundError

logger = logging.getLogger(__name__)

# Alpaca timeframe mapping for the bars API
_TIMEFRAME_MAP = {
    "1m": "1Min",
    "5m": "5Min",
    "15m": "15Min",
    "1h": "1Hour",
    "4h": "4Hour",
    "1d": "1Day",
}

_DATA_BASE_URL = "https://data.alpaca.markets"


class AlpacaAdapter(BrokerAdapter):
    """Alpaca implementation of the broker adapter interface."""

    def __init__(self, rate_limiter: RateLimiter | None = None):
        cfg = get_market_data_config()
        self._api_key = cfg.alpaca_api_key
        self._api_secret = cfg.alpaca_api_secret
        self._base_url = cfg.alpaca_base_url.rstrip("/")
        self._rate_limiter = rate_limiter or RateLimiter(max_requests_per_minute=180)
        self._headers = {
            "APCA-API-KEY-ID": self._api_key,
            "APCA-API-SECRET-KEY": self._api_secret,
        }

    @property
    def broker_name(self) -> str:
        return "alpaca"

    @property
    def supported_markets(self) -> list[str]:
        return ["equities"]

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
                        "Alpaca rate limited (429) on %s, retrying in %ds (attempt %d/%d)",
                        url, wait, attempt + 1, max_retries,
                    )
                    await asyncio.sleep(wait)
                    await self._rate_limiter.acquire()
                    continue

                if resp.status_code == 404:
                    # Only raise SymbolNotFoundError for symbol-specific endpoints
                    path = url.split("/")[-1] if "/" in url else url
                    if "/stocks/" in url or "/instruments/" in url:
                        raise SymbolNotFoundError(path)
                    # For non-symbol endpoints (like /v2/assets), treat as a general error
                    raise MarketDataConnectionError(
                        "alpaca", f"HTTP 404 on {url}: {resp.text[:200]}"
                    )

                if 400 <= resp.status_code < 500:
                    logger.error("Alpaca client error %d on %s: %s", resp.status_code, url, resp.text)
                    raise MarketDataConnectionError(
                        "alpaca",
                        f"HTTP {resp.status_code} on {url}: {resp.text[:200]}",
                    )

                if resp.status_code >= 500:
                    logger.error("Alpaca server error %d on %s", resp.status_code, url)
                    raise MarketDataConnectionError(
                        "alpaca", f"HTTP {resp.status_code} on {url}"
                    )

                return resp.json()

            except httpx.TimeoutException:
                logger.error("Alpaca timeout on %s (attempt %d/%d)", url, attempt + 1, max_retries)
                if attempt == max_retries - 1:
                    raise MarketDataConnectionError("alpaca", f"Timeout on {url}")
            except (httpx.ConnectError, httpx.ReadError) as e:
                logger.error("Alpaca connection error on %s: %s", url, e)
                if attempt == max_retries - 1:
                    raise MarketDataConnectionError("alpaca", f"Connection error on {url}: {e}")

        raise MarketDataConnectionError("alpaca", f"Max retries exceeded on {url}")

    async def list_available_symbols(self) -> list[dict]:
        """Fetch all tradable symbols from Alpaca."""
        url = f"{self._base_url}/v2/assets"
        data = await self._request("GET", url, params={"status": "active"})

        symbols = []
        for asset in data:
            if not asset.get("tradable", False):
                continue
            symbols.append({
                "symbol": asset["symbol"],
                "name": asset.get("name", asset["symbol"]),
                "market": "equities",
                "exchange": asset.get("exchange"),
                "base_asset": None,
                "quote_asset": "USD",
                "broker": "alpaca",
                "status": "active",
                "options_enabled": bool(asset.get("options_enabled", False)),
            })

        logger.info("Alpaca: fetched %d tradable symbols", len(symbols))
        return symbols

    async def fetch_historical_bars(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
        limit: int | None = None,
    ) -> list[dict]:
        """Fetch historical OHLCV bars with pagination."""
        alpaca_tf = _TIMEFRAME_MAP.get(timeframe)
        if not alpaca_tf:
            raise ValueError(f"Unsupported timeframe: {timeframe}")

        all_bars = []
        page_token = None
        max_per_page = min(limit or 10000, 10000)

        while True:
            params = {
                "timeframe": alpaca_tf,
                "start": start.isoformat(),
                "end": end.isoformat(),
                "limit": max_per_page,
                "adjustment": "raw",
            }
            if page_token:
                params["page_token"] = page_token

            url = f"{_DATA_BASE_URL}/v2/stocks/{symbol}/bars"
            data = await self._request("GET", url, params=params)

            bars = data.get("bars") or []
            for bar in bars:
                all_bars.append({
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "ts": datetime.fromisoformat(bar["t"].replace("Z", "+00:00")),
                    "open": Decimal(str(bar["o"])),
                    "high": Decimal(str(bar["h"])),
                    "low": Decimal(str(bar["l"])),
                    "close": Decimal(str(bar["c"])),
                    "volume": Decimal(str(bar["v"])),
                })

            page_token = data.get("next_page_token")
            if not page_token or (limit and len(all_bars) >= limit):
                break

        if limit:
            all_bars = all_bars[:limit]

        return all_bars

    async def fetch_latest_bars_batch(
        self,
        symbols: list[str],
        timeframe: str = "1Day",
        limit: int = 1,
    ) -> dict[str, dict]:
        """Fetch the latest bar(s) for multiple symbols in one call.

        Batches into groups of 200 to respect API limits.
        Returns: {symbol: {open, high, low, close, volume, ...}}
        """
        result = {}
        batch_size = 200

        for i in range(0, len(symbols), batch_size):
            batch = symbols[i : i + batch_size]
            params = {
                "symbols": ",".join(batch),
                "timeframe": timeframe,
                "limit": limit,
            }

            url = f"{_DATA_BASE_URL}/v2/stocks/bars"
            data = await self._request("GET", url, params=params)

            bars_data = data.get("bars", {})
            for sym, bars in bars_data.items():
                if bars:
                    bar = bars[-1]  # latest bar
                    result[sym] = {
                        "open": Decimal(str(bar["o"])),
                        "high": Decimal(str(bar["h"])),
                        "low": Decimal(str(bar["l"])),
                        "close": Decimal(str(bar["c"])),
                        "volume": Decimal(str(bar["v"])),
                        "ts": bar["t"],
                    }

        return result

    async def fetch_option_chain(self, underlying_symbol: str) -> dict | None:
        """Fetch option chain snapshot for an underlying symbol."""
        url = f"{_DATA_BASE_URL}/v1beta1/options/snapshots/{underlying_symbol}"
        try:
            data = await self._request("GET", url)
        except SymbolNotFoundError:
            return None

        snapshots = data.get("snapshots", {})
        contracts = {}
        for contract_symbol, snap in snapshots.items():
            latest_quote = snap.get("latestQuote", {})
            latest_trade = snap.get("latestTrade", {})
            greeks = snap.get("greeks", {})

            contracts[contract_symbol] = {
                "symbol": contract_symbol,
                "underlying": underlying_symbol,
                "latest_price": Decimal(str(latest_trade.get("p", 0))),
                "bid": Decimal(str(latest_quote.get("bp", 0))),
                "ask": Decimal(str(latest_quote.get("ap", 0))),
                "volume": latest_trade.get("s", 0),
                "open_interest": snap.get("openInterest", 0),
                "implied_volatility": Decimal(str(greeks.get("iv", 0))),
                "delta": Decimal(str(greeks.get("delta", 0))),
                "gamma": Decimal(str(greeks.get("gamma", 0))),
                "theta": Decimal(str(greeks.get("theta", 0))),
                "vega": Decimal(str(greeks.get("vega", 0))),
            }

        return {
            "underlying": underlying_symbol,
            "contracts": contracts,
            "snapshot_count": len(contracts),
        }

    async def fetch_dividends(
        self,
        symbols: list[str],
        start_date: date,
        end_date: date,
    ) -> list[dict]:
        """Fetch dividend announcements from Alpaca corporate actions."""
        url = f"{self._base_url}/v2/corporate_actions/announcements"
        params = {
            "ca_types": "dividend",
            "since": start_date.isoformat(),
            "until": end_date.isoformat(),
        }

        data = await self._request("GET", url, params=params)

        results = []
        symbol_set = set(symbols) if symbols else None
        for ann in data:
            sym = ann.get("symbol", "")
            if symbol_set and sym not in symbol_set:
                continue

            results.append({
                "symbol": sym,
                "corporate_action_id": ann.get("id", ""),
                "ca_type": ann.get("ca_sub_type", "cash"),
                "declaration_date": ann.get("declaration_date"),
                "ex_date": ann.get("ex_date"),
                "record_date": ann.get("record_date"),
                "payable_date": ann.get("payable_date"),
                "cash_amount": Decimal(str(ann.get("cash", 0))),
                "stock_rate": Decimal(str(ann["rate"])) if ann.get("rate") else None,
                "status": "announced",
                "source": "alpaca",
            })

        logger.info("Alpaca: fetched %d dividend announcements", len(results))
        return results

    # === WebSocket operations ===

    async def subscribe_bars(self, symbols: list[str]) -> None:
        """Delegate to the WebSocket manager."""
        from app.market_data.startup import get_ws_manager

        mgr = get_ws_manager()
        if mgr is None:
            raise RuntimeError("WebSocket manager not initialized")
        await mgr.subscribe("alpaca", symbols)

    async def unsubscribe_bars(self, symbols: list[str]) -> None:
        """Delegate to the WebSocket manager."""
        from app.market_data.startup import get_ws_manager

        mgr = get_ws_manager()
        if mgr is None:
            raise RuntimeError("WebSocket manager not initialized")
        await mgr.unsubscribe("alpaca", symbols)

    async def get_connection_health(self) -> dict:
        """Return health status from the WebSocket manager for alpaca."""
        from app.market_data.startup import get_ws_manager

        mgr = get_ws_manager()
        if mgr is None:
            return {"broker": "alpaca", "status": "disconnected"}
        health = mgr.get_health()
        return health.get("alpaca", {"broker": "alpaca", "status": "disconnected"})
