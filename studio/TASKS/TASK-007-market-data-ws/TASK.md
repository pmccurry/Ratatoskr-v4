# TASK-007 — Market Data: WebSocket Manager, Bar Storage, Aggregation, and Health

## Task Status
- Builder:    [ ] not started
- Validator:  [ ] not started
- Librarian:  [ ] not started

## Objective

Implement the real-time market data ingestion pipeline: WebSocket connections
to Alpaca and OANDA, async bar processing queue, batch writer, timeframe
aggregation engine, health monitoring, and the market data startup sequence.

After this task:
- The system connects to Alpaca and OANDA WebSocket streams for bar data
- Incoming bars are queued, batched, and written to the database
- 1-minute bars are aggregated into higher timeframes (5m, 15m, 1h, 4h, 1d) on write
- The WebSocket manager handles reconnection with exponential backoff
- Gap backfill runs automatically after reconnection
- The health monitor tracks connection status, data freshness, and queue depth
- The /api/v1/market-data/health endpoint returns live health status
- The market data module has a startup sequence that initializes everything

This task completes the market data module.

## Read First

1. /studio/STUDIO/PROJECT_STATE.md
2. /studio/STUDIO/DECISIONS.md
3. /studio/STUDIO/GLOSSARY.md
4. /studio/SPECS/market_data_module_spec.md — PRIMARY SPEC, sections 3 (WebSocket), 4 (bar storage and aggregation), 7 (health monitoring), 8 (startup sequence)
5. /studio/SPECS/cross_cutting_specs.md
6. Review TASK-005 and TASK-006 BUILDER_OUTPUT.md to understand existing code

## Constraints

- Do NOT create models or logic for any other module
- Do NOT create, modify, or delete anything inside /studio (except BUILDER_OUTPUT.md)
- Do NOT modify /CLAUDE.md
- Do NOT modify the broker REST methods implemented in TASK-006
  (subscribe/unsubscribe/health methods are the scope here)
- All financial values use Decimal
- All timestamps are timezone-aware UTC
- The WebSocket manager must be resilient — disconnections are expected, not errors

---

## Deliverables

### 1. WebSocket Manager (backend/app/market_data/streams/manager.py)

Central coordinator for all WebSocket connections.

```python
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
    
    async def start(self, broker: str, symbols: list[str]) -> None:
        """Start streaming bars for a broker's symbols.
        
        1. Create the appropriate BrokerWebSocket
        2. Connect and subscribe to symbols
        3. Start the receive loop (as an asyncio task)
        4. Update health status
        """
    
    async def stop(self, broker: str | None = None) -> None:
        """Stop streaming. If broker=None, stop all."""
    
    async def subscribe(self, broker: str, symbols: list[str]) -> None:
        """Add symbols to an existing connection."""
    
    async def unsubscribe(self, broker: str, symbols: list[str]) -> None:
        """Remove symbols from an existing connection."""
    
    def get_health(self) -> dict:
        """Return health status for all connections."""
    
    async def _receive_loop(self, broker: str) -> None:
        """Receive bars from WebSocket, push to queue.
        
        Runs as an asyncio task. On disconnection:
        1. Record disconnect time
        2. Update health status
        3. Start reconnection loop
        """
    
    async def _reconnect(self, broker: str) -> None:
        """Reconnect with exponential backoff.
        
        Backoff: initial_delay * (multiplier ^ attempt)
        Cap at max_delay.
        After successful reconnection:
        1. Re-subscribe to all symbols
        2. Trigger gap backfill for the disconnection period
        3. Update health status
        """
```

### 2. Broker WebSocket Abstraction (backend/app/market_data/streams/base.py)

Abstract base for broker-specific WebSocket connections.

```python
class BrokerWebSocket(ABC):
    """Abstract WebSocket connection to a broker."""
    
    @abstractmethod
    async def connect(self) -> None:
        """Establish the WebSocket connection and authenticate."""
    
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
        """Receive the next message. Returns parsed bar dict or None on disconnect."""
    
    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Whether the connection is currently alive."""
    
    @property
    @abstractmethod
    def subscribed_symbols(self) -> list[str]:
        """Currently subscribed symbols."""
```

### 3. Alpaca WebSocket (backend/app/market_data/streams/alpaca_ws.py)

Alpaca-specific WebSocket implementation.

```python
class AlpacaWebSocket(BrokerWebSocket):
    """Alpaca real-time bar streaming via WebSocket.
    
    URL: wss://stream.data.alpaca.markets/v2/sip
    Auth: send {"action": "auth", "key": api_key, "secret": api_secret}
    Subscribe: send {"action": "subscribe", "bars": [symbols]}
    Messages: {"T": "b", "S": symbol, "o": open, "h": high, "l": low,
               "c": close, "v": volume, "t": timestamp}
    """
```

Key implementation details:
- Connect and authenticate via JSON auth message
- Subscribe/unsubscribe via JSON messages
- Parse incoming bar messages into standardized dict format
- Convert prices to Decimal, timestamps to UTC
- Handle ping/pong for keepalive
- Return None from receive() on connection close

### 4. OANDA WebSocket (backend/app/market_data/streams/oanda_ws.py)

OANDA-specific streaming implementation.

```python
class OandaWebSocket(BrokerWebSocket):
    """OANDA real-time pricing stream.
    
    OANDA uses HTTP streaming (chunked transfer), not WebSocket.
    URL: {stream_url}/v3/accounts/{account_id}/pricing/stream
    Params: instruments=EUR_USD,GBP_USD,...
    Auth: Bearer token header
    
    Despite the class name, this uses httpx streaming for compatibility
    with the BrokerWebSocket interface.
    """
```

Key implementation details:
- OANDA streams pricing via HTTP chunked transfer, not true WebSocket
- Use httpx async streaming to read the chunked response
- Parse PRICE messages (ignore HEARTBEAT messages for data, but use
  heartbeats for liveness detection)
- OANDA streams bid/ask ticks, not bars — accumulate ticks into 1m bars:
  - Track open (first tick of minute), high, low, close (last tick), volume=0
  - When the minute boundary crosses, emit the completed bar
  - Use mid price: (bid + ask) / 2
- Convert all prices to Decimal
- Handle stream disconnection (httpx will raise on broken connection)

### 5. Bar Processing Queue (backend/app/market_data/streams/processor.py)

Async consumer that reads bars from the queue and writes them to the database.

```python
class BarProcessor:
    """Processes incoming bars from the WebSocket queue.
    
    Reads bars from the async queue, batches them, and writes
    to the database using the OHLCVBarRepository.upsert_bars() method.
    Also triggers aggregation for completed timeframe windows.
    """
    
    def __init__(
        self,
        bar_queue: asyncio.Queue,
        config: MarketDataConfig,
    ):
        self._queue = bar_queue
        self._config = config
        self._batch: list[dict] = []
        self._last_flush: float = 0
    
    async def start(self) -> None:
        """Start the processing loop as an asyncio task.
        
        Loop:
        1. Read bar from queue (with timeout)
        2. Add to batch
        3. If batch_size reached OR batch_interval elapsed:
           a. Convert batch to OHLCVBar model instances
           b. Call upsert_bars() to write
           c. For each written bar, check if aggregation is needed
           d. Clear batch
        """
    
    async def stop(self) -> None:
        """Flush remaining batch and stop."""
    
    async def _flush_batch(self, db: AsyncSession) -> None:
        """Write current batch to database and trigger aggregation."""
    
    async def _check_aggregation(self, db: AsyncSession, bar: dict) -> None:
        """Check if a completed higher-timeframe window exists.
        
        After writing a 1m bar, check if any higher timeframe windows
        just completed (e.g., at minute :05, a 5m window completed).
        If so, trigger aggregation for that window.
        """
```

Batch configuration:
- BAR_BATCH_WRITE_SIZE: flush when batch reaches this count (default 100)
- BAR_BATCH_WRITE_INTERVAL_SEC: flush at this interval even if batch is small (default 3)

### 6. Aggregation Engine (backend/app/market_data/aggregation/engine.py)

Builds higher-timeframe bars from 1-minute bars.

```python
class AggregationEngine:
    """Aggregates 1m bars into higher timeframes.
    
    Supported aggregations:
      1m → 5m, 15m, 1h, 4h, 1d
    
    All aggregations are computed directly from 1m bars (not cascading).
    This prevents compounding rounding errors.
    """
    
    async def aggregate_window(
        self,
        db: AsyncSession,
        symbol: str,
        timeframe: str,
        window_start: datetime,
    ) -> OHLCVBar | None:
        """Aggregate a specific timeframe window from 1m bars.
        
        1. Determine window boundaries (start, end) for the given timeframe
        2. Fetch all 1m bars within the window from the database
        3. If insufficient bars (window not complete), return None
        4. Compute: open=first open, high=max high, low=min low,
           close=last close, volume=sum volume
        5. Create aggregated OHLCVBar with is_aggregated=True
        6. Upsert into ohlcv_bars table
        7. Return the aggregated bar
        """
    
    def get_window_start(self, ts: datetime, timeframe: str) -> datetime:
        """Calculate the window start for a timestamp and timeframe.
        
        Examples:
          ts=10:37, timeframe=5m  → 10:35
          ts=10:37, timeframe=15m → 10:30
          ts=10:37, timeframe=1h  → 10:00
          ts=10:37, timeframe=4h  → 08:00 (aligned to midnight)
          ts=10:37, timeframe=1d  → 00:00
        """
    
    def is_window_complete(self, ts: datetime, timeframe: str) -> bool:
        """Check if the bar at ts completes a higher-timeframe window.
        
        A 5m window completes at minutes :00, :05, :10, :15, etc.
        (specifically, when the LAST 1m bar of the window arrives)
        
        Examples:
          ts=10:04, timeframe=5m  → True (bar at :04 is last of :00-:04)
          ts=10:03, timeframe=5m  → False
          ts=10:59, timeframe=1h  → True
          ts=10:58, timeframe=1h  → False
        """
    
    def get_required_timeframes(self) -> list[str]:
        """Return the list of timeframes to aggregate: ['5m', '15m', '1h', '4h', '1d']"""
```

**Critical rule:** All aggregations are computed from 1m bars directly.
5m is NOT built from 1m→5m. 15m is NOT built from 5m. Every higher
timeframe reads the underlying 1m bars and aggregates fresh. This
prevents compounding precision errors across aggregation levels
(DECISION-013).

### 7. Connection Health Tracking (backend/app/market_data/streams/health.py)

Tracks per-broker connection health and per-symbol data freshness.

```python
@dataclass
class ConnectionHealth:
    broker: str
    status: str  # "connected" | "disconnected" | "reconnecting"
    connected_since: datetime | None
    last_message_at: datetime | None
    subscribed_symbols: int
    reconnect_attempts: int
    last_disconnect_at: datetime | None

class HealthMonitor:
    """Monitors market data health.
    
    Runs as a periodic background task checking:
    - Connection status per broker
    - Data freshness per symbol (is the latest bar recent enough?)
    - Queue depth (is the bar processing queue backing up?)
    """
    
    def __init__(self, ws_manager: WebSocketManager, bar_queue: asyncio.Queue,
                 config: MarketDataConfig):
        ...
    
    async def start(self) -> None:
        """Start the health check loop (runs every health_check_interval seconds)."""
    
    async def stop(self) -> None:
        """Stop the health check loop."""
    
    async def get_health_status(self, db: AsyncSession) -> dict:
        """Return complete health report.
        
        Returns:
        {
            "overall_status": "healthy" | "degraded" | "unhealthy",
            "connections": {
                "alpaca": ConnectionHealth,
                "oanda": ConnectionHealth
            },
            "stale_symbols": [list of symbols with stale data],
            "write_pipeline": {
                "queue_depth": N,
                "queue_capacity": N,
                "queue_utilization_percent": N,
                "status": "healthy" | "warning" | "critical"
            },
            "backfill": {
                "pending_jobs": N,
                "running_jobs": N,
                "failed_jobs": N
            }
        }
        """
    
    async def _check_stale_symbols(self, db: AsyncSession) -> list[str]:
        """Find symbols where the latest bar is older than the stale threshold.
        
        Only check during market hours for equities.
        Forex is 24/5 so always check (except weekends).
        """
```

**Overall status logic:**
- healthy: all connections up, no stale symbols, queue utilization < warn%
- degraded: one connection down OR stale symbols exist OR queue > warn%
- unhealthy: all connections down OR queue > critical%

### 8. Implement Adapter WebSocket Methods

Update the Alpaca and OANDA adapters (from TASK-006) to implement
the WebSocket-related methods that were left as NotImplementedError:

**backend/app/market_data/adapters/alpaca.py:**
```python
async def subscribe_bars(self, symbols: list[str]) -> None:
    # Delegate to ws_manager.subscribe("alpaca", symbols)

async def unsubscribe_bars(self, symbols: list[str]) -> None:
    # Delegate to ws_manager.unsubscribe("alpaca", symbols)

async def get_connection_health(self) -> dict:
    # Return health status from ws_manager for "alpaca"
```

**backend/app/market_data/adapters/oanda.py:**
```python
# Same pattern for OANDA
```

Note: The adapters need a reference to the WebSocketManager. This can
be set after construction (e.g., `adapter.set_ws_manager(manager)`) or
the adapters can look it up from a module-level singleton. Choose the
simplest approach that avoids circular imports.

### 9. Market Data Startup Sequence (backend/app/market_data/startup.py)

Orchestrates the full market data module initialization.

```python
async def start_market_data(db: AsyncSession) -> None:
    """Market data module startup sequence.
    
    Called from FastAPI lifespan on application start.
    
    Steps:
    1. Load market data config
    2. Run universe filter (update watchlist)
    3. Get active watchlist symbols (grouped by broker)
    4. Check for backfill needs (new symbols, gaps)
    5. Run initial backfill if needed
    6. Create the bar processing queue
    7. Start the bar processor
    8. Start the WebSocket manager (connect to brokers, subscribe to symbols)
    9. Start the health monitor
    10. Log startup complete with symbol counts
    """

async def stop_market_data() -> None:
    """Graceful shutdown of market data module.
    
    Steps:
    1. Stop health monitor
    2. Stop WebSocket manager (close all connections)
    3. Stop bar processor (flush remaining batch)
    4. Log shutdown complete
    """
```

### 10. Register Startup in main.py

Update the FastAPI lifespan in backend/app/main.py to call the
market data startup/shutdown:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ... existing startup (settings, etc.)
    await start_market_data(db)
    yield
    await stop_market_data()
```

The startup should be wrapped in a try/except — if market data fails
to start (e.g., no API keys configured), log the error but don't crash
the entire application. Other modules should still work.

### 11. Update Health Endpoint

Replace the 501 stub for the health endpoint:

```
GET /api/v1/market-data/health → calls health_monitor.get_health_status()
                                  returns MarketDataHealthResponse
```

### 12. Fix OANDA Adapter Minor Issue from TASK-006

The Validator noted in TASK-006 that the OANDA adapter sends both `to`
and `count` parameters in fetch_historical_bars, which may conflict.
Fix this: when `to` (end date) is provided, omit `count`. When only
`from` (start date) is provided, use `count` to limit results.

---

## Acceptance Criteria

1. WebSocketManager coordinates connections to both Alpaca and OANDA
2. WebSocketManager start/stop methods create and destroy connections
3. WebSocketManager subscribe/unsubscribe routes to correct broker connection
4. WebSocketManager reconnects with exponential backoff on disconnection
5. Reconnection backoff uses configured initial_delay, max_delay, and multiplier
6. Gap backfill triggers automatically after successful reconnection
7. BrokerWebSocket abstract base class defines connect/disconnect/subscribe/unsubscribe/receive
8. AlpacaWebSocket authenticates and subscribes via JSON messages over WebSocket
9. AlpacaWebSocket parses bar messages, converts to Decimal/UTC
10. OandaWebSocket handles HTTP chunked streaming (not true WebSocket)
11. OandaWebSocket accumulates ticks into 1m bars at minute boundaries
12. OandaWebSocket converts bid/ask to mid prices as Decimal
13. BarProcessor reads from async queue and batches writes
14. BarProcessor flushes at batch_size OR batch_interval (whichever comes first)
15. BarProcessor calls upsert_bars for database writes
16. BarProcessor triggers aggregation check after each flush
17. AggregationEngine computes higher timeframes from 1m bars ONLY (not cascading)
18. AggregationEngine supports 5m, 15m, 1h, 4h, 1d aggregation
19. AggregationEngine correctly calculates window boundaries (alignment)
20. Aggregated bars have is_aggregated=True
21. Aggregated bars are upserted (not duplicated if re-aggregated)
22. HealthMonitor tracks per-broker connection status
23. HealthMonitor detects stale symbols (data freshness check)
24. HealthMonitor reports queue depth and utilization
25. HealthMonitor considers market hours for equity staleness checks
26. Overall health status computed correctly (healthy/degraded/unhealthy)
27. GET /api/v1/market-data/health returns live health data (no longer 501)
28. Alpaca adapter subscribe_bars/unsubscribe_bars/get_connection_health implemented
29. OANDA adapter subscribe_bars/unsubscribe_bars/get_connection_health implemented
30. Market data startup sequence initializes all components in order
31. Market data shutdown gracefully stops all components
32. Startup failure does not crash the application (logged, other modules still work)
33. Startup registered in main.py lifespan
34. OANDA fetch_historical_bars `to`/`count` parameter conflict fixed
35. All financial values use Decimal
36. All timestamps are timezone-aware UTC
37. No models or logic for other modules created
38. Nothing inside /studio modified (except BUILDER_OUTPUT.md)

---

## Required Output

When complete, write BUILDER_OUTPUT.md to this task's directory:
/studio/TASKS/TASK-007-market-data-ws/BUILDER_OUTPUT.md

Use the template from /studio/AGENTS/builder/OUTPUT_TEMPLATE.md
Fill in EVERY section. Leave nothing blank.
