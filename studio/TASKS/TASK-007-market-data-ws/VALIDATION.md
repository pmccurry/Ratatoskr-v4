# Validation Report — TASK-007

## Task
Market Data: WebSocket Manager, Bar Storage, Aggregation, and Health

## Pre-Flight Checks
- [x] Task packet read completely
- [x] Builder output read completely
- [x] All referenced specs read
- [x] DECISIONS.md read
- [x] GLOSSARY.md read
- [x] cross_cutting_specs.md read
- [x] Repo files independently inspected (not just builder summary)

---

## 1. Builder Output Quality

### Is BUILDER_OUTPUT.md complete?
- [x] Completion Checklist present and filled
- [x] Files Created section present and non-empty
- [x] Files Modified section present
- [x] Files Deleted section present
- [x] Acceptance Criteria Status — every criterion listed and marked
- [x] Assumptions section present (7 assumptions documented)
- [x] Ambiguities section present (explicit "None")
- [x] Dependencies section present (explicit "None")
- [x] Tests section present (explains verification approach)
- [x] Risks section present (4 risks documented)
- [x] Deferred Items section present (explicit "None")
- [x] Recommended Next Task section present (TASK-008)

Section Result: PASS
Issues: None

---

## 2. Acceptance Criteria Verification

| # | Criterion | Builder Claims | Validator Verified | Status |
|---|-----------|---------------|-------------------|--------|
| 1 | WebSocketManager coordinates connections to both Alpaca and OANDA | Yes | Yes — manager.py has _connections dict, _create_connection factory returns AlpacaWebSocket/OandaWebSocket | PASS |
| 2 | WebSocketManager start/stop methods create and destroy connections | Yes | Yes — start() creates BrokerWebSocket, connects, subscribes, launches task; stop() cancels tasks, disconnects | PASS |
| 3 | WebSocketManager subscribe/unsubscribe routes to correct broker connection | Yes | Yes — looks up connection by broker name, delegates | PASS |
| 4 | WebSocketManager reconnects with exponential backoff on disconnection | Yes | Yes — _reconnect method with configurable delays | PASS |
| 5 | Reconnection backoff uses configured initial_delay, max_delay, and multiplier | Yes | Yes — reads ws_reconnect_initial_delay, ws_reconnect_max_delay, ws_reconnect_backoff_multiplier from config | PASS |
| 6 | Gap backfill triggers automatically after successful reconnection | Yes | Yes — _gap_backfill called via asyncio.create_task after reconnect with disconnect/reconnect timestamps | PASS |
| 7 | BrokerWebSocket abstract base class defines connect/disconnect/subscribe/unsubscribe/receive | Yes | Yes — base.py has ABC with 5 abstract methods + 2 abstract properties (is_connected, subscribed_symbols) | PASS |
| 8 | AlpacaWebSocket authenticates and subscribes via JSON messages over WebSocket | Yes | Yes — connect sends auth JSON, subscribe sends subscribe JSON, uses websockets library | PASS |
| 9 | AlpacaWebSocket parses bar messages, converts to Decimal/UTC | Yes | Yes — T="b" parsing, Decimal(str(...)) for prices, fromisoformat for timestamps | PASS |
| 10 | OandaWebSocket handles HTTP chunked streaming (not true WebSocket) | Yes | Yes — httpx async streaming, aiter_lines | PASS |
| 11 | OandaWebSocket accumulates ticks into 1m bars at minute boundaries | Yes | Yes — _process_tick tracks OHLC per minute_key, emits on boundary cross | PASS |
| 12 | OandaWebSocket converts bid/ask to mid prices as Decimal | Yes | Yes — mid = (bid + ask) / Decimal("2") | PASS |
| 13 | BarProcessor reads from async queue and batches writes | Yes | Yes — _process_loop reads with 1s timeout, accumulates in _batch list | PASS |
| 14 | BarProcessor flushes at batch_size OR batch_interval (whichever comes first) | Yes | Yes — checks both: len >= batch_size or elapsed >= batch_interval | PASS |
| 15 | BarProcessor calls upsert_bars for database writes | Yes | Yes — _flush_batch converts to OHLCVBar, calls _bar_repo.upsert_bars | PASS |
| 16 | BarProcessor triggers aggregation check after each flush | Yes | Yes — _check_aggregation called for each 1m bar in flushed batch | PASS |
| 17 | AggregationEngine computes higher timeframes from 1m bars ONLY (not cascading) | Yes | Yes — aggregate_window always fetches 1m bars from DB | PASS |
| 18 | AggregationEngine supports 5m, 15m, 1h, 4h, 1d aggregation | Yes | Yes — get_required_timeframes returns all five, _TIMEFRAME_MINUTES has entries for all | PASS |
| 19 | AggregationEngine correctly calculates window boundaries (alignment) | Yes | Yes — get_window_start aligns correctly; aggregate_window now delegates to _compute_window_end (timedelta) for all timeframes (v1 bug fixed) | PASS |
| 20 | Aggregated bars have is_aggregated=True | Yes | Yes — set in aggregate_window (engine.py:96) | PASS |
| 21 | Aggregated bars are upserted (not duplicated if re-aggregated) | Yes | Yes — uses upsert_bars which does ON CONFLICT UPDATE | PASS |
| 22 | HealthMonitor tracks per-broker connection status | Yes | Yes — ConnectionHealth dataclass per broker, updated by WebSocketManager | PASS |
| 23 | HealthMonitor detects stale symbols (data freshness check) | Yes | Yes — _check_stale_symbols queries latest bar timestamp per watchlist symbol | PASS |
| 24 | HealthMonitor reports queue depth and utilization | Yes | Yes — queue_depth, queue_capacity, queue_utilization_percent in write_pipeline | PASS |
| 25 | HealthMonitor considers market hours for equity staleness checks | Yes | Yes — skips weekends, skips non-US-market-hours for equities UTC 13-21 | PASS |
| 26 | Overall health status computed correctly (healthy/degraded/unhealthy) | Yes | Yes — logic matches spec: unhealthy if all disconnected or queue critical; degraded if any disconnected/stale/queue warning; healthy otherwise | PASS |
| 27 | GET /api/v1/market-data/health returns live health data (no longer 501) | Yes | Yes — router calls _service.get_health(db), returns {"data": health} | PASS |
| 28 | Alpaca adapter subscribe_bars/unsubscribe_bars/get_connection_health implemented | Yes | Yes — delegates to WebSocketManager via lazy import get_ws_manager() | PASS |
| 29 | OANDA adapter subscribe_bars/unsubscribe_bars/get_connection_health implemented | Yes | Yes — same delegation pattern | PASS |
| 30 | Market data startup sequence initializes all components in order | Yes | Yes — startup.py: config -> universe filter -> watchlist -> backfill -> queue -> processor -> WS manager -> health monitor | PASS |
| 31 | Market data shutdown gracefully stops all components | Yes | Yes — reverse order: health -> WS -> processor | PASS |
| 32 | Startup failure does not crash the application (logged, other modules still work) | Yes | Yes — try/except in main.py lifespan, logs error but continues | PASS |
| 33 | Startup registered in main.py lifespan | Yes | Yes — start_market_data in startup, stop_market_data before engine dispose | PASS |
| 34 | OANDA fetch_historical_bars to/count parameter conflict fixed | Yes | Yes — count removed from params when to is provided (oanda.py:156 comment) | PASS |
| 35 | All financial values use Decimal | Yes | Yes — all prices in AlpacaWebSocket and OandaWebSocket use Decimal(str(...)) | PASS |
| 36 | All timestamps are timezone-aware UTC | Yes | Yes — fromisoformat with Z replacement, datetime.now(timezone.utc) throughout | PASS |
| 37 | No models or logic for other modules created | Yes | Yes — all files are within market_data module | PASS |
| 38 | Nothing inside /studio modified (except BUILDER_OUTPUT.md) | Yes | Yes — only BUILDER_OUTPUT.md written in studio | PASS |

Section Result: PASS
Issues: None

---

## 3. Scope Check

- [x] No files created outside task deliverables
- [x] No files modified outside task scope
- [x] No modules added that aren't in the approved list
- [x] No architectural changes or new patterns introduced
- [x] No live trading logic present
- [x] No dependencies added beyond what the task requires (websockets already in pyproject.toml)

Section Result: PASS
Issues: None

---

## 4. Naming Compliance

- [x] Python files use snake_case
- [x] Folder names match module specs (streams/, aggregation/)
- [x] Entity names match GLOSSARY exactly
- [x] Database-related names follow conventions
- [x] No typos in module or entity names
- [x] N/A — no TypeScript or frontend files

Section Result: PASS
Issues: None

---

## 5. Decision Compliance

- [x] No live trading logic (DECISION-002)
- [x] Tech stack matches approved stack (DECISIONS 007-009)
- [x] No Redis, microservices, or event bus
- [x] No off-scope modules (DECISION-001)
- [x] Python tooling uses uv (DECISION-010)
- [x] WebSocket streaming for real-time market data (DECISION-012)
- [x] Aggregation from 1m only, not cascading (DECISION-013) — engine correctly fetches 1m bars for all aggregations

Section Result: PASS
Issues: None

---

## 6. Structure and Convention Compliance

- [x] Folder structure matches cross_cutting_specs and market data module spec
- [x] File organization follows the defined module layout
- [x] __init__.py files exist in streams/ and aggregation/
- [x] No unexpected files in any directory

Section Result: PASS
Issues: None

---

## 7. Independent File Verification

### Files builder claims to have created that ACTUALLY EXIST:
All 8 verified:
- backend/app/market_data/streams/base.py
- backend/app/market_data/streams/alpaca_ws.py
- backend/app/market_data/streams/oanda_ws.py
- backend/app/market_data/streams/manager.py
- backend/app/market_data/streams/processor.py
- backend/app/market_data/streams/health.py
- backend/app/market_data/aggregation/engine.py
- backend/app/market_data/startup.py

### Files that EXIST but builder DID NOT MENTION:
- backend/app/market_data/streams/__init__.py (expected, not an issue)
- backend/app/market_data/aggregation/__init__.py (expected, not an issue)

### Files builder claims to have created that DO NOT EXIST:
None

Section Result: PASS
Issues: None

---

## Issues Summary

### Blockers (must fix before PASS)
None

### Major (should fix before proceeding)
None

### Minor (note for future, does not block)

**1. Stale docstring in service.py (line 4-5)**
Module docstring still says "Health monitoring remains as NotImplementedError until TASK-007" — but it's now implemented. Should be updated to reflect current state.

**2. BarProcessor source field inconsistency (processor.py:123)**
`source=b.get("market", "stream")` would set source to "equities"/"forex" (the market name) when bars come from the stream. However, the backfill runner (runner.py:164,238) sets source to the broker name ("alpaca"/"oanda"). These should be consistent — either both use broker name or both use market name. Recommend aligning to broker name for consistency.

**3. AlpacaWebSocket recursive receive() (alpaca_ws.py:161)**
When a WebSocket message batch contains no bar messages (T != "b"), the method recursively calls `await self.receive()`. With many consecutive non-bar messages (auth confirmations, subscription confirmations, errors), this could accumulate stack frames. An iterative loop (`while True: ... return bar`) would be safer.

---

## Risk Notes
- OANDA's HTTP streaming model means subscribe/unsubscribe requires disconnecting and reconnecting with the new instrument list (oanda_ws.py). This is inherent to the API design but adds latency to subscription changes.
- The market hours heuristic for equity staleness (UTC 13-21) is approximate and doesn't cover pre-market, after-hours, holidays, or half-day sessions. Noted by builder as a known limitation.
- The aggregation engine fetches 1m bars from the DB for each higher-timeframe window. Under high symbol counts, this generates many queries per flush cycle.

---

## Validation History

| Version | Date | Result | Notes |
|---------|------|--------|-------|
| v1 | 2026-03-13 | FAIL | Major: aggregation engine window_end uses replace(minute=N) which raises ValueError for 1h (always), 15m (25%), 5m (8%) |
| v2 | 2026-03-13 | PASS | Fix confirmed: engine.py:58 now delegates to _compute_window_end (timedelta) for all timeframes |

---

## RESULT: PASS

Task is ready for Librarian update. Three minor issues documented for future cleanup.
