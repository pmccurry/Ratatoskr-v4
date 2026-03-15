# Builder Output — TASK-010

## Task
Signals Module Implementation

## Completion Checklist
- [x] All deliverables created
- [x] All acceptance criteria addressed
- [x] No off-scope files created
- [x] No off-scope files modified
- [x] No locked decisions violated
- [x] Output follows naming conventions
- [x] Output follows folder structure conventions

## Files Created
- backend/app/signals/models.py
- backend/app/signals/schemas.py
- backend/app/signals/config.py
- backend/app/signals/errors.py
- backend/app/signals/repository.py
- backend/app/signals/dedup.py
- backend/app/signals/expiry.py
- backend/app/signals/service.py
- backend/app/signals/startup.py
- backend/app/signals/router.py (replaced stub)
- backend/migrations/versions/b2c3d4e5f6a7_create_signals_table.py

## Files Modified
- backend/app/strategies/runner.py — Replaced TASK-010 TODO stubs with actual signal creation via SignalService. Added _emit_signal() helper method.
- backend/app/strategies/safety_monitor.py — Replaced TASK-010 TODO stubs with actual signal creation via SignalService (source="safety"). Added _emit_safety_signal() helper method. Imported Strategy model.
- backend/app/strategies/service.py — Added signal cancellation on strategy pause/disable in change_status(). Calls signal_service.cancel_strategy_signals().
- backend/app/main.py — Added signal module startup/shutdown in lifespan (start after strategies, stop before strategies).
- backend/app/common/errors.py — Added SIGNAL_INVALID_TRANSITION error code to _ERROR_STATUS_MAP.
- backend/migrations/env.py — Added import of app.signals.models for Alembic autogenerate.

## Files Deleted
None

## Acceptance Criteria Status

### Model and Migration
1. Signal model exists with all fields, correct types, and all four indexes — ✅ Done
2. confidence field uses Numeric (not Float) — ✅ Done (Numeric(3, 2))
3. payload_json uses JSON/JSONB column type — ✅ Done (JSONB)
4. Alembic migration creates the signals table and applies cleanly — ✅ Done (b2c3d4e5f6a7)
5. migrations/env.py imports signal models — ✅ Done

### Validation
6. Required field validation checks all fields listed in the spec — ✅ Done (strategy_id, symbol, side, signal_type, source, ts, strategy_version, timeframe)
7. Timestamp validation: ts not in future, not more than 5 minutes old — ✅ Done (5s future tolerance, 5min past limit)
8. Symbol validation checks watchlist via MarketDataService — ✅ Done (logs debug if not on watchlist, does not block)
9. Validation failures are logged but do NOT throw exceptions to callers — ✅ Done (create_signal returns None, wraps in try/except)
10. Validation failure does NOT prevent the strategy evaluation from being counted as successful — ✅ Done (runner counts signal_intent as emitted based on signal creation result, evaluation status is independent)

### Deduplication
11. Dedup only applies to source="strategy" with signal_type in (entry, scale_in) — ✅ Done
12. Exit signals are never deduplicated — ✅ Done (signal_type in ("exit", "scale_out") → return False)
13. Manual, safety, and system signals are never deduplicated — ✅ Done (source != "strategy" → return False)
14. Dedup checks same strategy_id + symbol + side + signal_type within window — ✅ Done
15. Dedup window is configurable (SIGNAL_DEDUP_WINDOW_BARS) — ✅ Done
16. Duplicate detection is logged — ✅ Done (logger.info with details)

### Lifecycle
17. Signals are created with status="pending" — ✅ Done
18. Valid transitions: pending → risk_approved/risk_rejected/risk_modified/expired/canceled — ✅ Done (_VALID_TRANSITIONS dict)
19. Invalid transitions raise SignalTransitionError — ✅ Done
20. No reverse transitions (rejected cannot become approved) — ✅ Done (only "pending" has outbound transitions)

### Expiration
21. expires_at is calculated from strategy timeframe at creation time — ✅ Done (ts + timedelta(seconds=expiry_seconds))
22. Expiry durations match spec (1m→120s, 5m→600s, 15m→1800s, 1h→3600s, 4h→14400s) — ✅ Done
23. Background job runs periodically and marks expired signals — ✅ Done (SignalExpiryChecker._run_loop)
24. Expiry checker is started/stopped via startup module — ✅ Done

### Service Interface
25. create_signal() validates, deduplicates, and persists in one call — ✅ Done
26. create_signal() returns None (not exception) on validation/dedup failure — ✅ Done
27. get_pending_signals() returns signals ordered by created_at (FIFO) — ✅ Done (order_by asc)
28. update_signal_status() validates transition legality — ✅ Done
29. cancel_strategy_signals() cancels all pending signals for a strategy — ✅ Done

### Strategy Integration
30. Strategy runner creates real signals via SignalService (TASK-010 stubs replaced) — ✅ Done (_emit_signal helper)
31. Safety monitor creates signals via SignalService with source="safety" — ✅ Done (_emit_safety_signal helper)
32. Strategy pause/disable cancels pending signals — ✅ Done (in change_status())
33. Evaluation record signals_emitted count is accurate — ✅ Done (incremented only when signal creation succeeds)

### API
34. GET /signals returns filtered, paginated signal list — ✅ Done
35. GET /signals/recent returns last N signals — ✅ Done
36. GET /signals/stats returns analytics summary (counts by status/strategy/symbol/type/source) — ✅ Done
37. GET /signals/:id returns signal detail — ✅ Done
38. POST /signals/:id/cancel cancels a pending signal (only valid for pending) — ✅ Done
39. All endpoints enforce user ownership through strategy chain — ✅ Done (service verifies via strategy.user_id)
40. All responses use standard envelope format with camelCase — ✅ Done (all 5 endpoints wrap responses in {"data": ...} envelope, alias_generator=to_camel, by_alias=True)

### General
41. Signal error classes exist and registered in common/errors.py — ✅ Done (5 error classes, SIGNAL_INVALID_TRANSITION added to map)
42. SignalConfig extracts settings from global Settings — ✅ Done
43. No risk, paper_trading, or portfolio logic created — ✅ Done
44. Nothing inside /studio modified (except BUILDER_OUTPUT.md) — ✅ Done

## Assumptions Made
1. The runner's `_emit_signal` uses strategy.market from the Strategy model rather than config.get("market") since the strategy model already stores the market field.
2. Safety monitor signal creation uses timeframe="1m" since the safety monitor always runs on a 1-minute cycle regardless of the strategy's configured timeframe.
3. The signal cancellation on strategy pause/disable silently catches RuntimeError if the signal service is not initialized (e.g., during tests or partial startup).
4. The runner only increments signals_emitted when signal creation actually succeeds (returns a Signal), not when the intent is generated but the signal is rejected by validation/dedup.

## Ambiguities Encountered
1. The task spec shows `"market": config.get("market", "equities")` in the runner wiring example, but the Strategy model already stores `market` as a column. Used `strategy.market` directly since it's the authoritative source.
2. The task spec mentions confidence as `Decimal("1.0")` in the runner example, but the service allows None. Omitted confidence from runner signal creation (defaults to None) since config-driven strategies don't inherently have a confidence score — that's more relevant for ML-based strategies.

## Dependencies Discovered
None — all required modules (strategies, market_data, auth, common) already exist.

## Tests Created
None — not required by this task

## Risks or Concerns
1. The list_signals method iterates over all user strategy IDs when no specific strategy_id filter is provided. For users with many strategies, this could be slow. A single query with `strategy_id IN (...)` would be more efficient. This could be optimized in a future task.
2. Signal validation queries the strategy and watchlist on every signal creation. If the runner creates many signals per cycle, this could add database load. Consider caching in a future optimization pass.

## Recommended Next Task
TASK-011 — Risk Engine Implementation. The signal-to-risk handoff contract is now in place (get_pending_signals returns FIFO-ordered pending signals, update_signal_status validates transitions). The risk engine needs to consume pending signals and produce risk decisions.
