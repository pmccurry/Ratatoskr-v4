# Builder Output — TASK-007

## Task
Market Data: WebSocket Manager, Bar Storage, Aggregation, and Health

## Completion Checklist
- [x] All deliverables created
- [x] All acceptance criteria addressed
- [x] No off-scope files created
- [x] No off-scope files modified
- [x] No locked decisions violated
- [x] Output follows naming conventions
- [x] Output follows folder structure conventions

## Files Created

backend/app/market_data/streams/base.py
backend/app/market_data/streams/alpaca_ws.py
backend/app/market_data/streams/oanda_ws.py
backend/app/market_data/streams/manager.py
backend/app/market_data/streams/processor.py
backend/app/market_data/streams/health.py
backend/app/market_data/aggregation/engine.py
backend/app/market_data/startup.py

## Files Modified

backend/app/market_data/adapters/alpaca.py — replaced NotImplementedError WebSocket stubs with delegation to WebSocketManager via startup.get_ws_manager()
backend/app/market_data/adapters/oanda.py — replaced NotImplementedError WebSocket stubs with delegation to WebSocketManager; fixed to/count parameter conflict in fetch_historical_bars (removed count when to is set)
backend/app/market_data/service.py — implemented get_health() (was NotImplementedError), now delegates to HealthMonitor; added db parameter
backend/app/market_data/router.py — replaced 501 health endpoint stub with live health data endpoint (calls service.get_health, returns MarketDataHealthResponse in data envelope)
backend/app/main.py — added market data startup/shutdown to FastAPI lifespan (start_market_data on startup, stop_market_data on shutdown, wrapped in try/except)

## Files Deleted
None

## Acceptance Criteria Status
1. WebSocketManager coordinates connections to both Alpaca and OANDA — ✅ Done (start/stop/subscribe/unsubscribe per broker, _create_connection factory)
2. WebSocketManager start/stop methods create and destroy connections — ✅ Done (start creates BrokerWebSocket, connects, subscribes, launches receive loop; stop cancels tasks and disconnects)
3. WebSocketManager subscribe/unsubscribe routes to correct broker connection — ✅ Done (looks up connection by broker name, delegates to BrokerWebSocket)
4. WebSocketManager reconnects with exponential backoff on disconnection — ✅ Done (_reconnect method with configurable initial_delay, max_delay, multiplier)
5. Reconnection backoff uses configured initial_delay, max_delay, and multiplier — ✅ Done (reads ws_reconnect_initial_delay, ws_reconnect_max_delay, ws_reconnect_backoff_multiplier from config)
6. Gap backfill triggers automatically after successful reconnection — ✅ Done (_gap_backfill called via asyncio.create_task after reconnect, uses backfill_gap for each symbol with disconnect/reconnect timestamps)
7. BrokerWebSocket abstract base class defines connect/disconnect/subscribe/unsubscribe/receive — ✅ Done (ABC with 5 abstract methods + 2 abstract properties)
8. AlpacaWebSocket authenticates and subscribes via JSON messages over WebSocket — ✅ Done (connect sends auth JSON, subscribe sends subscribe JSON, uses websockets library)
9. AlpacaWebSocket parses bar messages, converts to Decimal/UTC — ✅ Done (T="b" message parsing, Decimal(str(...)) for prices, fromisoformat for timestamps)
10. OandaWebSocket handles HTTP chunked streaming (not true WebSocket) — ✅ Done (httpx async streaming, aiter_lines for chunked response)
11. OandaWebSocket accumulates ticks into 1m bars at minute boundaries — ✅ Done (_process_tick tracks open/high/low/close per minute_key, emits on boundary cross)
12. OandaWebSocket converts bid/ask to mid prices as Decimal — ✅ Done (mid = (bid + ask) / Decimal("2"))
13. BarProcessor reads from async queue and batches writes — ✅ Done (_process_loop reads with 1s timeout, accumulates in _batch list)
14. BarProcessor flushes at batch_size OR batch_interval (whichever comes first) — ✅ Done (checks both conditions: len >= batch_size or elapsed >= batch_interval)
15. BarProcessor calls upsert_bars for database writes — ✅ Done (_flush_batch converts to OHLCVBar models, calls _bar_repo.upsert_bars)
16. BarProcessor triggers aggregation check after each flush — ✅ Done (_check_aggregation called for each 1m bar in the flushed batch)
17. AggregationEngine computes higher timeframes from 1m bars ONLY (not cascading) — ✅ Done (aggregate_window always fetches 1m bars from DB, never from intermediate timeframes)
18. AggregationEngine supports 5m, 15m, 1h, 4h, 1d aggregation — ✅ Done (get_required_timeframes returns all five)
19. AggregationEngine correctly calculates window boundaries (alignment) — ✅ Done (get_window_start aligns to midnight-based intervals; _compute_window_end uses timedelta for all timeframes; verified: 10:37→10:35 for 5m, →10:30 for 15m, →10:00 for 1h, →08:00 for 4h, →00:00 for 1d; edge cases verified: 5m at :55, 15m at :45, 1h at :00 all cross hour boundary correctly)
20. Aggregated bars have is_aggregated=True — ✅ Done (set in aggregate_window)
21. Aggregated bars are upserted (not duplicated if re-aggregated) — ✅ Done (uses upsert_bars which does ON CONFLICT UPDATE)
22. HealthMonitor tracks per-broker connection status — ✅ Done (ConnectionHealth dataclass per broker, updated by WebSocketManager)
23. HealthMonitor detects stale symbols (data freshness check) — ✅ Done (_check_stale_symbols queries latest bar timestamp per watchlist symbol)
24. HealthMonitor reports queue depth and utilization — ✅ Done (queue_depth, queue_capacity, queue_utilization_percent in write_pipeline)
25. HealthMonitor considers market hours for equity staleness checks — ✅ Done (skips weekends, skips non-US-market-hours for equities UTC 13-21)
26. Overall health status computed correctly (healthy/degraded/unhealthy) — ✅ Done (unhealthy: all disconnected or queue critical; degraded: any disconnected or stale or queue warning; healthy: all good)
27. GET /api/v1/market-data/health returns live health data (no longer 501) — ✅ Done (router calls service.get_health, returns in data envelope)
28. Alpaca adapter subscribe_bars/unsubscribe_bars/get_connection_health implemented — ✅ Done (delegates to WebSocketManager via startup.get_ws_manager())
29. OANDA adapter subscribe_bars/unsubscribe_bars/get_connection_health implemented — ✅ Done (same delegation pattern)
30. Market data startup sequence initializes all components in order — ✅ Done (config → universe filter → backfill → queue → processor → WS manager → health monitor)
31. Market data shutdown gracefully stops all components — ✅ Done (health monitor → WS manager → bar processor, in reverse order)
32. Startup failure does not crash the application (logged, other modules still work) — ✅ Done (try/except in main.py lifespan, logs error but continues)
33. Startup registered in main.py lifespan — ✅ Done (start_market_data in startup, stop_market_data before engine dispose)
34. OANDA fetch_historical_bars `to`/`count` parameter conflict fixed — ✅ Done (removed count from params when to is provided)
35. All financial values use Decimal — ✅ Done (all prices in AlpacaWebSocket and OandaWebSocket use Decimal(str(...)))
36. All timestamps are timezone-aware UTC — ✅ Done (fromisoformat with Z replacement, datetime.now(timezone.utc) throughout)
37. No models or logic for other modules created — ✅ Done
38. Nothing inside /studio modified (except BUILDER_OUTPUT.md) — ✅ Done

## Assumptions Made
- AlpacaWebSocket uses the `websockets` library (already in pyproject.toml dependencies) for true WebSocket connections. The library handles ping/pong keepalive automatically.
- OANDA's streaming endpoint uses httpx's async streaming (aiter_lines) to read the HTTP chunked transfer encoding. This is consistent with the existing httpx dependency.
- OANDA tick-to-bar accumulation uses volume=0 since OANDA pricing stream ticks don't carry volume data. This matches the existing OANDA REST adapter behavior.
- The gap backfill after reconnection only backfills 1m bars (not higher timeframes). Higher timeframes will be re-aggregated when the 1m bars are processed through the normal pipeline.
- Market hours check for equity staleness uses approximate US market hours in UTC (13:30-20:00 simplified to 13-21). This is a rough heuristic; a more precise check would need a market calendar.
- The startup sequence creates its own database session via get_session_factory() rather than receiving one from the lifespan, since the startup runs initial backfill and universe filter which need their own transaction scope.
- Adapter WebSocket methods use lazy imports (`from app.market_data.startup import get_ws_manager`) to avoid circular imports between adapters and the startup module.

## Ambiguities Encountered
None — task and specs were unambiguous for all deliverables.

## Dependencies Discovered
None — all dependencies were available (websockets and httpx already in pyproject.toml).

## Tests Created
None — not required by this task. Verified functionality through import checks, aggregation engine unit tests (window start, window complete), and adapter/service/router import verification.

## Risks or Concerns
- The Alpaca WebSocket message format (T="b" for bars) is based on current API documentation. If Alpaca changes the message schema, AlpacaWebSocket.receive() will need updating.
- OANDA's HTTP streaming can be sensitive to network conditions; long-running HTTP connections may be interrupted by proxies or load balancers. The reconnection logic handles this.
- The aggregation engine fetches 1m bars from the database for each higher-timeframe window. Under high symbol counts, this could generate many queries during flush. If performance becomes an issue, the aggregation could be batched or use in-memory caching.
- The market hours heuristic for staleness checking (UTC 13-21) doesn't account for pre-market/after-hours trading, holidays, or half-day sessions.

## Deferred Items
None — all deliverables complete.

## Recommended Next Task
TASK-008 — Strategy module: indicator library, condition engine, formula parser. The market data module is now complete with REST adapters, WebSocket streaming, bar storage, aggregation, and health monitoring.
