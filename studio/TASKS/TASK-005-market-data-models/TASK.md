# TASK-005 — Market Data: Models, Schemas, and Broker Abstraction

## Task Status
- Builder:    [ ] not started
- Validator:  [ ] not started
- Librarian:  [ ] not started

## Objective

Implement the foundational layer of the market data module: database models,
Pydantic schemas, the broker adapter abstraction (base interface), and the
module's internal configuration.

After this task:
- All market data database tables exist (market_symbols, watchlist_entries,
  ohlcv_bars, backfill_jobs, dividend_announcements)
- The broker adapter interface is defined (abstract base class)
- Pydantic schemas exist for all market data entities
- The market data module has its own config class
- Alembic migration creates all tables
- The market data router has placeholder endpoints defined (not implemented yet)

This task creates the DATA LAYER and ABSTRACTIONS only. No WebSocket connections,
no broker API calls, no bar ingestion, no backfill execution. Those come in
TASK-006 and TASK-007.

## Read First

1. /studio/STUDIO/PROJECT_STATE.md
2. /studio/STUDIO/DECISIONS.md
3. /studio/STUDIO/GLOSSARY.md
4. /studio/SPECS/market_data_module_spec.md — PRIMARY SPEC, read completely
5. /studio/SPECS/cross_cutting_specs.md — error handling, API conventions, repository pattern
6. /studio/SPECS/auth_module_spec.md — reference for how TASK-004 structured a module (pattern to follow)

## Constraints

- Do NOT implement WebSocket connections or streaming logic
- Do NOT implement broker API calls (no Alpaca or OANDA HTTP calls)
- Do NOT implement the universe filter execution logic
- Do NOT implement the backfill runner execution logic
- Do NOT implement bar aggregation logic
- Do NOT implement the health monitoring system
- Do NOT implement option chain fetching or caching
- Do NOT create models or logic for any other module
- Do NOT create, modify, or delete anything inside /studio (except BUILDER_OUTPUT.md)
- Do NOT modify /CLAUDE.md
- Follow the repository pattern: router → service → repository → database
- Follow the API conventions from cross_cutting_specs
- Use DomainError subclasses for errors (not raw HTTPException)
- All financial values use Decimal, never float
- All timestamps are UTC, timezone-aware

---

## Deliverables

### 1. Market Data Models (backend/app/market_data/models.py)

All models inherit from BaseModel (common/base_model.py).

**MarketSymbol:**
```
MarketSymbol:
  - id: UUID (from BaseModel)
  - symbol: str (e.g., "AAPL", "EUR_USD")
  - name: str (human-readable, e.g., "Apple Inc.", "Euro / US Dollar")
  - market: str ("equities" | "forex")
  - exchange: str, nullable (e.g., "NYSE", "NASDAQ")
  - base_asset: str, nullable (e.g., "EUR" for EUR_USD)
  - quote_asset: str, nullable (e.g., "USD" for EUR_USD)
  - broker: str ("alpaca" | "oanda")
  - status: str ("active" | "inactive", default "active")
  - options_enabled: bool (default false)
  - created_at: datetime (from BaseModel)
  - updated_at: datetime (from BaseModel)

Indexes:
  UNIQUE (symbol, market, broker)
  INDEX (market, status)
  INDEX (broker, status)
```

**WatchlistEntry:**
```
WatchlistEntry:
  - id: UUID (from BaseModel)
  - symbol: str
  - market: str ("equities" | "forex")
  - broker: str ("alpaca" | "oanda")
  - status: str ("active" | "inactive", default "active")
  - added_at: datetime
  - removed_at: datetime, nullable (soft-delete for audit trail)
  - filter_metadata_json: JSON, nullable (why it passed filter — volume, price, etc.)
  - created_at: datetime (from BaseModel)
  - updated_at: datetime (from BaseModel)

Indexes:
  INDEX (symbol, market, broker, status)
  INDEX (status)
```

**OHLCVBar:**
```
OHLCVBar:
  - id: UUID (from BaseModel)
  - symbol: str
  - market: str ("equities" | "forex")
  - timeframe: str ("1m" | "5m" | "15m" | "1h" | "4h" | "1d")
  - ts: datetime (bar open timestamp, UTC, timezone-aware)
  - open: Numeric (use SQLAlchemy Numeric for Decimal precision)
  - high: Numeric
  - low: Numeric
  - close: Numeric
  - volume: Numeric
  - source: str ("alpaca" | "oanda")
  - is_aggregated: bool (default false)
  - created_at: datetime (from BaseModel)

  Note: NO updated_at on this model — bars are written once (or upserted),
  not regularly updated. Keeping it lean since this will be the largest table.

Indexes:
  UNIQUE (symbol, timeframe, ts)
  INDEX (symbol, timeframe, ts) — primary query pattern for strategy reads
```

**BackfillJob:**
```
BackfillJob:
  - id: UUID (from BaseModel)
  - symbol: str
  - market: str
  - timeframe: str
  - start_date: datetime
  - end_date: datetime
  - status: str ("pending" | "running" | "completed" | "failed")
  - bars_fetched: int (default 0)
  - started_at: datetime, nullable
  - completed_at: datetime, nullable
  - error_message: str, nullable
  - retry_count: int (default 0)
  - created_at: datetime (from BaseModel)
  - updated_at: datetime (from BaseModel)

Indexes:
  INDEX (symbol, timeframe, status)
  INDEX (status)
```

**DividendAnnouncement:**
```
DividendAnnouncement:
  - id: UUID (from BaseModel)
  - symbol: str
  - corporate_action_id: str (Alpaca's persistent ID across updates)
  - ca_type: str ("cash" | "stock")
  - declaration_date: date
  - ex_date: date
  - record_date: date
  - payable_date: date
  - cash_amount: Numeric (per share, for cash dividends)
  - stock_rate: Numeric, nullable (for stock dividends)
  - status: str ("announced" | "confirmed" | "paid" | "canceled")
  - source: str ("alpaca")
  - fetched_at: datetime
  - created_at: datetime (from BaseModel)
  - updated_at: datetime (from BaseModel)

Indexes:
  INDEX (symbol, ex_date)
  INDEX (ex_date)
  INDEX (payable_date)
  INDEX (status)
  UNIQUE (corporate_action_id)
```

**Important: Use SQLAlchemy `Numeric` column type for all price/financial fields
(open, high, low, close, volume, cash_amount, stock_rate). This maps to
PostgreSQL NUMERIC which stores exact decimal values. Do NOT use Float.**

### 2. Market Data Schemas (backend/app/market_data/schemas.py)

Pydantic models for request/response. Use camelCase aliases for JSON.
Use `Decimal` type for financial fields in Pydantic models.

```
Response schemas:
  MarketSymbolResponse: id, symbol, name, market, exchange, base_asset,
    quote_asset, broker, status, options_enabled, created_at
  
  WatchlistEntryResponse: id, symbol, market, broker, status, added_at,
    removed_at, filter_metadata_json, created_at
  
  OHLCVBarResponse: id, symbol, market, timeframe, ts, open, high, low,
    close, volume, source, is_aggregated, created_at
    (Decimal fields serialized as strings for JSON precision)
  
  BackfillJobResponse: id, symbol, market, timeframe, start_date, end_date,
    status, bars_fetched, started_at, completed_at, error_message,
    retry_count, created_at
  
  DividendAnnouncementResponse: id, symbol, corporate_action_id, ca_type,
    declaration_date, ex_date, record_date, payable_date, cash_amount,
    stock_rate, status, source, created_at
  
  MarketDataHealthResponse: overall_status, connections (dict),
    stale_symbols (list), write_pipeline (dict), backfill (dict)
    (matches health status object from market_data_module_spec section 7)

Query/filter schemas:
  BarQueryParams: symbol (required), timeframe (required),
    limit (optional, default 200, max 10000),
    start (optional, datetime), end (optional, datetime)
  
  WatchlistQueryParams: market (optional), status (optional),
    page, page_size
```

### 3. Broker Adapter Interface (backend/app/market_data/adapters/base.py)

Abstract base class defining the contract every broker adapter must implement.

```python
from abc import ABC, abstractmethod
from decimal import Decimal
from datetime import datetime, date

class BrokerAdapter(ABC):
    """Abstract interface for broker data adapters.
    
    Every broker (Alpaca, OANDA) implements this interface.
    The market data service routes to the correct adapter based
    on the symbol's market (equities → Alpaca, forex → OANDA).
    """
    
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
```

### 4. Adapter Stubs (not implemented, just interface compliance)

Create stub files that will be implemented in TASK-006/007:

**backend/app/market_data/adapters/alpaca.py:**
```python
"""Alpaca broker adapter — equities, options.

Implementation in TASK-006 (REST) and TASK-007 (WebSocket).
"""

from app.market_data.adapters.base import BrokerAdapter


class AlpacaAdapter(BrokerAdapter):
    """Alpaca implementation of the broker adapter interface."""
    
    @property
    def broker_name(self) -> str:
        return "alpaca"
    
    @property
    def supported_markets(self) -> list[str]:
        return ["equities"]
    
    # All abstract methods raise NotImplementedError
    # with message "Alpaca adapter not yet implemented — see TASK-006/007"
```

**backend/app/market_data/adapters/oanda.py:**
```python
"""OANDA broker adapter — forex.

Implementation in TASK-006 (REST) and TASK-007 (WebSocket).
"""
# Same pattern as Alpaca stub
```

### 5. Market Data Repository (backend/app/market_data/repository.py)

Database access layer for all market data models.

```python
class MarketSymbolRepository:
    async def get_by_symbol(self, db, symbol: str, market: str) -> MarketSymbol | None
    async def get_all(self, db, market: str | None = None, status: str = "active") -> list[MarketSymbol]
    async def create(self, db, symbol: MarketSymbol) -> MarketSymbol
    async def update(self, db, symbol: MarketSymbol) -> MarketSymbol
    async def upsert(self, db, symbol: MarketSymbol) -> MarketSymbol

class WatchlistRepository:
    async def get_active(self, db, market: str | None = None) -> list[WatchlistEntry]
    async def get_by_symbol(self, db, symbol: str) -> WatchlistEntry | None
    async def add(self, db, entry: WatchlistEntry) -> WatchlistEntry
    async def deactivate(self, db, symbol: str) -> None  # soft-delete: set removed_at
    async def get_paginated(self, db, market: str | None, status: str | None,
                            page: int, page_size: int) -> tuple[list[WatchlistEntry], int]

class OHLCVBarRepository:
    async def get_bars(self, db, symbol: str, timeframe: str,
                       limit: int = 200, start: datetime | None = None,
                       end: datetime | None = None) -> list[OHLCVBar]
    async def get_latest_close(self, db, symbol: str, timeframe: str = "1m") -> Decimal | None
    async def upsert_bars(self, db, bars: list[OHLCVBar]) -> int  # bulk upsert, returns count
    async def get_latest_timestamp(self, db, symbol: str, timeframe: str) -> datetime | None

class BackfillJobRepository:
    async def create(self, db, job: BackfillJob) -> BackfillJob
    async def update(self, db, job: BackfillJob) -> BackfillJob
    async def get_pending(self, db) -> list[BackfillJob]
    async def get_by_symbol(self, db, symbol: str, timeframe: str) -> BackfillJob | None
    async def get_all(self, db, status: str | None = None) -> list[BackfillJob]

class DividendAnnouncementRepository:
    async def upsert(self, db, announcement: DividendAnnouncement) -> DividendAnnouncement
    async def get_upcoming(self, db, symbol: str | None = None,
                           days_ahead: int = 30) -> list[DividendAnnouncement]
    async def get_by_ex_date(self, db, ex_date: date) -> list[DividendAnnouncement]
    async def get_by_payable_date(self, db, payable_date: date) -> list[DividendAnnouncement]
```

**Important for OHLCVBarRepository.upsert_bars():**
Use PostgreSQL `INSERT ... ON CONFLICT (symbol, timeframe, ts) DO UPDATE`
for the upsert. This is the batch write path that the WebSocket bar
processor will use. It must handle conflicts gracefully.

### 6. Market Data Errors (backend/app/market_data/errors.py)

```python
class SymbolNotFoundError(DomainError):
    # code: MARKET_DATA_SYMBOL_NOT_FOUND, status: 404

class MarketDataStaleError(DomainError):
    # code: MARKET_DATA_STALE, status: 503

class BackfillFailedError(DomainError):
    # code: MARKET_DATA_BACKFILL_FAILED, status: 500

class ConnectionError(DomainError):
    # code: MARKET_DATA_CONNECTION_ERROR, status: 503
```

Register these in common/errors.py error-to-status mapping.

### 7. Market Data Config (backend/app/market_data/config.py)

A config class that extracts market-data-specific settings from the
global Settings object. This provides a clean interface so the module
doesn't reference the global settings directly.

```python
from app.common.config import get_settings

class MarketDataConfig:
    """Market data module configuration."""
    
    def __init__(self):
        s = get_settings()
        # Broker credentials
        self.alpaca_api_key = s.alpaca_api_key
        self.alpaca_api_secret = s.alpaca_api_secret
        self.alpaca_base_url = s.alpaca_base_url
        self.alpaca_data_ws_url = s.alpaca_data_ws_url
        self.oanda_access_token = s.oanda_access_token
        self.oanda_account_id = s.oanda_account_id
        self.oanda_base_url = s.oanda_base_url
        self.oanda_stream_url = s.oanda_stream_url
        # Universe filter
        self.equities_min_volume = s.universe_filter_equities_min_volume
        self.equities_min_price = s.universe_filter_equities_min_price
        self.equities_exchanges = s.universe_filter_equities_exchanges
        # WebSocket
        self.ws_reconnect_initial_delay = s.ws_reconnect_initial_delay_sec
        self.ws_reconnect_max_delay = s.ws_reconnect_max_delay_sec
        self.ws_reconnect_backoff_multiplier = s.ws_reconnect_backoff_multiplier
        self.ws_heartbeat_interval = s.ws_heartbeat_interval_sec
        self.ws_stale_threshold = s.ws_stale_data_threshold_sec
        self.ws_bar_queue_max_size = s.ws_bar_queue_max_size
        # Bar storage
        self.bar_batch_write_size = s.bar_batch_write_size
        self.bar_batch_write_interval = s.bar_batch_write_interval_sec
        # Backfill
        self.backfill_1m_days = s.backfill_1m_days
        self.backfill_1h_days = s.backfill_1h_days
        self.backfill_4h_days = s.backfill_4h_days
        self.backfill_1d_days = s.backfill_1d_days
        self.backfill_rate_limit_buffer = s.backfill_rate_limit_buffer_percent
        self.backfill_max_retries = s.backfill_max_retries
        self.backfill_retry_delay = s.backfill_retry_delay_sec
        # Options
        self.option_cache_ttl = s.option_cache_ttl_sec
        # Health
        self.stale_threshold = s.market_data_stale_threshold_sec
        self.stale_check_interval = s.market_data_stale_check_interval_sec
        self.queue_warn_percent = s.market_data_queue_warn_percent
        self.queue_critical_percent = s.market_data_queue_critical_percent
        self.health_check_interval = s.market_data_health_check_interval_sec
        # Corporate actions
        self.corporate_actions_lookforward_days = s.corporate_actions_lookforward_days


def get_market_data_config() -> MarketDataConfig:
    return MarketDataConfig()
```

### 8. Market Data Service Stub (backend/app/market_data/service.py)

Create the service class with method signatures matching the inter-module
interface contract from cross_cutting_specs.md. Methods raise
NotImplementedError for now — they'll be implemented across TASK-006 and TASK-007.

```python
class MarketDataService:
    """Market data service — inter-module interface.
    
    Other modules call these methods. Implementation across TASK-006/007.
    """
    
    async def get_bars(self, db, symbol, timeframe, limit=None, start=None, end=None):
        """Get OHLCV bars for a symbol. Used by: strategy runner, portfolio MTM."""
        # This one CAN be implemented now — it's a DB read via repository
        # Implement it: query OHLCVBarRepository.get_bars()
    
    async def get_latest_close(self, db, symbol, timeframe="1m"):
        """Get the most recent close price. Used by: paper trading, portfolio MTM."""
        # This one CAN be implemented now — DB read
        # Implement it: query OHLCVBarRepository.get_latest_close()
    
    async def is_symbol_on_watchlist(self, db, symbol):
        """Check if a symbol is on the active watchlist. Used by: risk, signals."""
        # This one CAN be implemented now — DB read
        # Implement it: query WatchlistRepository.get_by_symbol()
    
    async def get_watchlist(self, db, market=None):
        """Get the current active watchlist. Used by: strategy runner."""
        # This one CAN be implemented now — DB read
        # Implement it: query WatchlistRepository.get_active()
    
    async def get_health(self):
        """Get market data health status. Used by: strategy runner, dashboard."""
        raise NotImplementedError("Health monitoring — see TASK-007")
    
    async def get_option_chain(self, underlying_symbol):
        """Get option chain snapshot. Used by: strategy runner (options strategies)."""
        raise NotImplementedError("Option chain fetching — see TASK-006")
    
    async def get_upcoming_dividends(self, db, symbol=None):
        """Get upcoming dividend announcements. Used by: strategy runner, portfolio."""
        # This one CAN be implemented now — DB read
        # Implement it: query DividendAnnouncementRepository.get_upcoming()
    
    async def get_dividend_yield(self, db, symbol):
        """Get annualized dividend yield. Used by: strategy indicators."""
        raise NotImplementedError("Dividend yield calculation — see TASK-006")
    
    async def get_next_ex_date(self, db, symbol):
        """Get next ex-dividend date. Used by: strategy indicators."""
        # This one CAN be implemented now — DB read
        # Implement it: query upcoming dividends, return nearest ex_date
```

**Note:** Methods that are pure database reads should be implemented now
since the repositories exist. Methods that require broker API calls or
complex computation are left as NotImplementedError with references to
future tasks.

### 9. Market Data Router (backend/app/market_data/router.py)

Replace the empty router stub with defined endpoints. Endpoints that
depend on unimplemented service methods should return 501 Not Implemented.
Endpoints backed by database reads should work.

```
GET /api/v1/market-data/health          → 501 (not yet implemented)
GET /api/v1/market-data/watchlist        → paginated watchlist (works — DB read)
GET /api/v1/market-data/bars             → query bars (works — DB read)
GET /api/v1/market-data/symbols          → list symbols (works — DB read)
GET /api/v1/market-data/backfill/status  → backfill job status (works — DB read)
GET /api/v1/market-data/dividends        → upcoming dividends (works — DB read)
POST /api/v1/market-data/backfill/trigger  → 501 (not yet implemented)
POST /api/v1/market-data/watchlist/refresh → 501 (not yet implemented)
```

All endpoints require authentication (Depends(get_current_user)).
POST endpoints require admin (Depends(require_admin)).
All responses use the standard envelope format.
The bars endpoint accepts BarQueryParams (symbol, timeframe, limit, start, end).

### 10. Alembic Migration

Create migration for all five market data tables.

```bash
cd backend
alembic revision --autogenerate -m "create_market_data_tables"
```

Verify migration applies cleanly:
```bash
alembic upgrade head
```

### 11. Register Models for Alembic

Update backend/migrations/env.py to import market_data models
so Alembic autogenerate can discover them:

```python
import app.auth.models       # existing
import app.market_data.models  # add this
```

---

## Acceptance Criteria

1. MarketSymbol model exists with all fields, unique constraint on (symbol, market, broker)
2. WatchlistEntry model exists with all fields, proper indexes
3. OHLCVBar model exists with all Numeric fields (not Float), unique constraint on (symbol, timeframe, ts)
4. BackfillJob model exists with all fields and status tracking
5. DividendAnnouncement model exists with all fields, unique on corporate_action_id
6. All financial fields (open, high, low, close, volume, cash_amount, stock_rate) use SQLAlchemy Numeric type
7. Alembic migration creates all five tables and applies cleanly
8. BrokerAdapter abstract base class defines all methods from the spec
9. Alpaca and OANDA adapter stubs exist, inherit from BrokerAdapter, raise NotImplementedError
10. All Pydantic response schemas exist with camelCase aliases
11. BarQueryParams schema validates symbol (required), timeframe (required), limit (default 200, max 10000)
12. MarketDataConfig extracts all market-data settings from global Settings
13. All five repository classes exist with complete method signatures
14. OHLCVBarRepository.upsert_bars uses INSERT ON CONFLICT for bulk upsert
15. MarketDataService has all inter-module interface methods defined
16. Service methods backed by DB reads are implemented (get_bars, get_latest_close, is_symbol_on_watchlist, get_watchlist, get_upcoming_dividends, get_next_ex_date)
17. Service methods requiring broker calls raise NotImplementedError with task reference
18. Market data router endpoints exist with correct auth dependencies
19. DB-backed endpoints return data in standard envelope format
20. Unimplemented endpoints return 501
21. Market data error classes exist and are registered in common error mapping
22. Alembic env.py imports market_data models
23. No WebSocket, broker API, or backfill execution logic implemented
24. No models or logic for other modules created
25. Nothing inside /studio modified (except BUILDER_OUTPUT.md)

---

## Required Output

When complete, write BUILDER_OUTPUT.md to this task's directory:
/studio/TASKS/TASK-005-market-data-models/BUILDER_OUTPUT.md

Use the template from /studio/AGENTS/builder/OUTPUT_TEMPLATE.md
Fill in EVERY section. Leave nothing blank.
