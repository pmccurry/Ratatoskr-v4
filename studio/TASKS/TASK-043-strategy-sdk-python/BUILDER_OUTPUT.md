# Builder Output — TASK-043

## Task
Strategy SDK + Python Strategy Runner

## Completion Checklist
- [x] All deliverables created
- [x] All acceptance criteria addressed
- [x] No off-scope files created
- [x] No off-scope files modified
- [x] No locked decisions violated
- [x] Output follows naming conventions
- [x] Output follows folder structure conventions

## Files Created
- `backend/app/strategy_sdk/__init__.py` — Module init
- `backend/app/strategy_sdk/base.py` — Strategy ABC with lifecycle hooks, signal builder, state helpers, parameter declaration
- `backend/app/strategy_sdk/signal.py` — StrategySignal dataclass with all pipeline-required fields
- `backend/app/strategy_sdk/indicators.py` — Pandas-based indicator helpers accepting DataFrame + source param (SMA, sma_series, EMA, RSI, ATR, Bollinger, MACD, highest, lowest, crosses_above/below with NaN-safe scalar comparisons)
- `backend/app/strategy_sdk/utils.py` — TimeUtils (hour_et, minute_et, date_et, weekday, is_between_hours) and PipUtils (pip_value, to_pips, from_pips, candle_body_pct, candle_direction)
- `backend/app/strategy_sdk/registry.py` — Strategy discovery from strategies/ folder, global registration, instance management
- `backend/app/strategy_sdk/runner.py` — PythonStrategyRunner with start/stop/on_new_bar, signal pipeline integration via session factory
- `backend/app/strategy_sdk/router.py` — 5 API endpoints (list, detail, start, stop, status)
- `strategies/__init__.py` — Empty init
- `strategies/example_sma_cross.py` — Working SMA Crossover example with configurable periods, crossover detection, SL/TP
- `strategies/README.md` — SDK documentation with quick start, DataFrame-based indicator API, crossover example, all helper methods documented

## Files Modified
- `backend/pyproject.toml` — Added pandas>=2.0.0 to dependencies
- `backend/app/main.py` — Added python_strategy_router import, strategy discovery in lifespan (non-fatal), router registration

## Files Deleted
None

## Acceptance Criteria Status
1. AC1: Strategy base class exists with on_bar(), on_start(), on_stop(), on_fill() lifecycle hooks — ✅ Done
2. AC2: StrategySignal dataclass has all fields needed by the signal pipeline — ✅ Done (strategy_name, symbol, direction, entry_price, stop_loss, take_profit, quantity, metadata, timestamp, score, confidence)
3. AC3: Indicators class provides SMA, EMA, RSI, ATR, Bollinger, MACD, highest, lowest, crosses_above/below — ✅ Done (all methods accept DataFrame + source param; crossover helpers use float() scalar comparisons with NaN guards)
4. AC4: TimeUtils provides hour_et, is_between_hours, date_et, weekday — ✅ Done
5. AC5: PipUtils provides to_pips, from_pips, pip_value (with JPY handling), candle_body_pct — ✅ Done
6. AC6: Registry discovers Python strategy files from strategies/ folder on startup — ✅ Done
7. AC7: Strategy classes with name set are auto-registered; files without valid strategies skipped — ✅ Done (try/except per file, logs errors)
8. AC8: GET /api/v1/python-strategies returns list of discovered strategies — ✅ Done
9. AC9: POST /api/v1/python-strategies/{name}/start starts a strategy — ✅ Done
10. AC10: POST /api/v1/python-strategies/{name}/stop stops a strategy — ✅ Done
11. AC11: Runner's on_new_bar() calls strategy.on_bar() for matching symbol/timeframe — ✅ Done
12. AC12: Signals from Python strategies are submitted to the existing signal service — ✅ Done (via session factory pattern)
13. AC13: Example SMA Crossover strategy exists in strategies/ and is discoverable — ✅ Done
14. AC14: strategies/README.md documents the SDK with all available helpers — ✅ Done
15. AC15: Backend startup log shows "Found N Python strategies" — ✅ Done
16. AC16: Existing condition-based strategies NOT affected — ✅ Done (no changes to backend/app/strategies/)
17. AC17: Nothing inside /studio modified (except BUILDER_OUTPUT.md) — ✅ Done

## Assumptions Made
- Used `zoneinfo.ZoneInfo` (Python 3.12 stdlib) instead of pytz for timezone handling
- Runner's `_get_positions`, `_get_equity`, `_get_cash` are implemented as stubs returning defaults — will be wired to real portfolio service when market data integration is done
- The `_process_signal` method uses the session factory pattern (matching alert engine) to obtain db sessions for signal creation
- The `/status/all` route is defined before `/{name}` to avoid FastAPI parameter matching conflicts
- Strategy discovery runs in the lifespan startup (non-fatal — failure doesn't prevent backend from starting)

## Ambiguities Encountered
- The task mentions the runner should hook into the market data bar stream but doesn't specify exactly where. The `on_new_bar()` method is ready to be called but the actual hookup to the WebSocket manager's bar processing pipeline is deferred — it requires modifying market_data/streams code which is out of scope.

## Dependencies Discovered
- Added `pandas>=2.0.0` to pyproject.toml (required by indicators.py for Series/DataFrame operations)

## Tests Created
None — not required by this task

## Risks or Concerns
- The market data stream hookup (calling `on_new_bar()` when bars arrive) is not yet wired. This will need a follow-up to integrate with `market_data/streams/manager.py`.
- Strategy state is in-memory only — resets on backend restart. Noted as acceptable for V1 per task spec.

## Deferred Items
- Market data stream hookup (calling runner.on_new_bar from bar processing pipeline)
- Portfolio service integration for live positions/equity/cash in runner

## Recommended Next Task
TASK-044 (backtest integration for Python strategies) or the market data hookup for live execution.
