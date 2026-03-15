# Builder Output — TASK-014

## Task
Observability Module Implementation

## Completion Checklist
- [x] All deliverables created
- [x] All acceptance criteria addressed
- [x] No off-scope files created
- [x] No off-scope files modified
- [x] No locked decisions violated
- [x] Output follows naming conventions
- [x] Output follows folder structure conventions

## Files Created
- backend/app/observability/models.py
- backend/app/observability/config.py
- backend/app/observability/errors.py
- backend/app/observability/schemas.py
- backend/app/observability/service.py
- backend/app/observability/startup.py
- backend/app/observability/events/emitter.py
- backend/app/observability/events/repository.py
- backend/app/observability/metrics/collector.py
- backend/app/observability/metrics/repository.py
- backend/app/observability/alerts/engine.py
- backend/app/observability/alerts/repository.py
- backend/app/observability/alerts/notifications.py
- backend/app/observability/alerts/seed.py
- backend/app/observability/logging/config.py
- backend/migrations/versions/b2c3d4e5f6a7_create_observability_tables.py

## Files Modified
- backend/app/observability/router.py — Replaced stub with 12 full endpoints: events (list, recent, detail), health (system, pipeline), metrics (list, timeseries), alerts (list, active, acknowledge), alert-rules (list, update)
- backend/app/main.py — Added observability startup FIRST (before market_data) and shutdown LAST (after market_data, before engine dispose)
- backend/app/common/errors.py — Registered 3 error codes: OBSERVABILITY_EVENT_NOT_FOUND (404), OBSERVABILITY_ALERT_RULE_NOT_FOUND (404), OBSERVABILITY_ALERT_NOT_FOUND (404)
- backend/migrations/env.py — Added `import app.observability.models` for Alembic autogenerate

## Files Deleted
None

## Acceptance Criteria Status

### Models and Migration
1. AuditEvent model exists with all fields and seven indexes — ✅ Done
2. AuditEvent has no updated_at (immutable, append-only) — ✅ Done (inherits from Base directly, not BaseModel)
3. MetricDatapoint model exists with all fields — ✅ Done
4. AlertRule model exists with condition_config as JSON — ✅ Done
5. AlertInstance model exists with lifecycle tracking fields — ✅ Done
6. Alembic migration creates all four tables and applies cleanly — ✅ Done (b2c3d4e5f6a7)

### Event Emission
7. EventEmitter.emit() is non-blocking (puts on async queue) — ✅ Done (put_nowait with overflow handling)
8. Batch writer drains queue and writes in configurable batch sizes — ✅ Done (_batch_writer)
9. Batch writer flushes at batch_size OR interval (whichever first) — ✅ Done (wait_for timeout + drain loop)
10. Queue overflow drops debug first, then info, NEVER drops warning+ — ✅ Done (_handle_overflow checks severity < 2)
11. Queue overflow logs a meta-event about dropped events — ✅ Done (logs warning every 100 drops)

### Event Storage and Query
12. Events are immutable (no update or delete via service) — ✅ Done (service only has get methods)
13. Event queries support filtering by category, severity, event_type, strategy_id, symbol, date range — ✅ Done
14. Recent events query supports limit and severity filter — ✅ Done (severity_gte filtering)
15. Event retention cleanup deletes old events based on config — ✅ Done (cleanup_expired_events on EventEmitter)

### Metrics Collection
16. MetricsCollector runs periodically at configured interval — ✅ Done (_run_loop with asyncio.sleep)
17. Collector gathers metrics from multiple module interfaces — ✅ Done (portfolio, strategies, signals, paper_trading, system)
18. Metric datapoints stored with name, type, value, labels, timestamp — ✅ Done
19. Metric time series queryable by name, date range, labels — ✅ Done (get_timeseries)
20. Metric retention cleanup deletes old datapoints — ✅ Done (cleanup_expired_metrics)

### Alert Engine
21. Alert engine evaluates enabled rules at configured interval — ✅ Done (_run_loop)
22. event_match condition type triggers on matching events — ✅ Done (_evaluate_event_match)
23. metric_threshold condition type triggers when value exceeds threshold for duration — ✅ Done (_evaluate_metric_threshold)
24. absence condition type triggers when expected event doesn't occur in window — ✅ Done (_evaluate_absence)
25. Cooldown prevents re-alerting within configured window — ✅ Done (cooldown_elapsed check)
26. Auto-resolve clears alerts when triggering condition no longer met — ✅ Done (resolve call when condition_met=False)

### Alert Management
27. AlertInstance created with status=active when rule triggers — ✅ Done
28. Acknowledgment sets acknowledged_at and acknowledged_by — ✅ Done
29. Resolution sets resolved_at — ✅ Done
30. Active alerts queryable for dashboard banners — ✅ Done (get_active)

### Notifications
31. Dashboard notifications stored in DB (read by frontend) — ✅ Done (_send_dashboard returns True)
32. Webhook notifications sent via httpx POST with correct payload — ✅ Done (_send_webhook)
33. Email notifications logged for MVP (actual SMTP deferred) — ✅ Done (_send_email logs content)
34. Notification channels configurable per rule — ✅ Done (notification_channels JSON field)

### Built-In Rules
35. All critical built-in rules seeded on startup (~4 rules) — ✅ Done (kill switch, safety monitor, catastrophic drawdown, WebSocket disconnect)
36. All error built-in rules seeded (~5 rules) — ✅ Done (auto-paused, broker fallback, daily loss, drawdown, queue backpressure)
37. All warning built-in rules seeded (~6 rules) — ✅ Done (stale symbols, drawdown approaching, daily loss approaching, signal expired, queue elevated, forex pool)
38. Rules are created only if they don't already exist (idempotent seed) — ✅ Done (get_by_name check)

### API
39. GET /observability/events returns filtered, paginated events — ✅ Done
40. GET /observability/events/recent returns activity feed — ✅ Done
41. GET /observability/events/:id returns event detail — ✅ Done
42. GET /observability/health returns system health summary — ✅ Done
43. GET /observability/health/pipeline returns per-module status — ✅ Done
44. GET /observability/metrics lists available metrics — ✅ Done
45. GET /observability/metrics/:name returns time series — ✅ Done
46. GET /observability/alerts returns filtered alert instances — ✅ Done
47. GET /observability/alerts/active returns active alerts — ✅ Done
48. POST /observability/alerts/:id/ack acknowledges an alert — ✅ Done
49. GET /observability/alert-rules returns all rules — ✅ Done
50. PUT /observability/alert-rules/:id updates a rule (admin only) — ✅ Done
51. All responses use {"data": ...} envelope with camelCase — ✅ Done

### Integration
52. Observability starts FIRST in main.py lifespan — ✅ Done (before market_data)
53. Observability stops LAST in main.py lifespan — ✅ Done (after market_data, before engine dispose)
54. get_event_emitter() returns the emitter singleton for other modules — ✅ Done
55. Application logging configured (JSON/text format, stdout) — ✅ Done (configure_logging in startup)

### General
56. ObservabilityConfig loads all settings — ✅ Done
57. Error classes exist and registered in common/errors.py — ✅ Done
58. Nothing inside /studio modified (except BUILDER_OUTPUT.md) — ✅ Done

## Assumptions Made
1. **System health checks**: Module availability is checked by dynamically importing each module's startup getter function and checking if it returns a non-None service. This avoids hard-coding module dependencies.
2. **Metrics collection scope**: For MVP, the collector queries database models directly (Position count, Strategy count, Signal count, PaperOrder/PaperFill counts) rather than going through service layer, to avoid circular dependencies. All queries are wrapped in try/except to be non-fatal.
3. **Event queue overflow meta-event**: Instead of trying to emit a meta-event (which would also overflow), the overflow is logged via Python logging every 100 drops.
4. **Metric timeseries resolution**: For MVP, the `resolution` parameter is accepted but not used for aggregation — raw datapoints are returned. Time-bucket aggregation is a future enhancement.
5. **Webhook dependency**: The webhook notification uses httpx (already in the project for broker API calls) for POST requests with a 10-second timeout.
6. **Alert seeding timing**: Alert rules are seeded during observability startup using its own database session from get_session_factory(), which is available at that point in the lifespan.

## Ambiguities Encountered
1. **Partial indexes in migration**: The task spec's AuditEvent model defines partial indexes (WHERE strategy_id IS NOT NULL, WHERE symbol IS NOT NULL). These are created using `postgresql_where=sa.text(...)` in the migration, which is PostgreSQL-specific.
2. **Metric name path parameter**: Metric names use dot notation (e.g., "system.uptime_seconds"). Used `{metric_name:path}` in the route to allow dots in the URL path segment.

## Dependencies Discovered
None — all required modules and models exist.

## Tests Created
None — not required by this task.

## Risks or Concerns
1. **Batch writer error handling**: If the batch writer fails to write events, they are dropped from the batch (logged but lost). A more robust implementation would retry or persist to a fallback store.
2. **Alert evaluation performance**: The alert engine queries the database for each rule on every evaluation cycle. With many rules and high-frequency evaluation, this could become a bottleneck.
3. **Metric datapoint volume**: At 60-second collection intervals with ~10 metrics per cycle, the metric_datapoints table will grow by ~14,400 rows per day. The 90-day retention cleanup mitigates this.

## Deferred Items
- Wiring emit() calls into other modules' business logic (future incremental task)
- SMTP email integration (logged for MVP)
- Time-bucket aggregation for metric time series
- Metric collection from market data module (connection status, stale symbols, bar write rate)

## Recommended Next Task
TASK-015 — Frontend Shell and Navigation. This completes the backend modules and transitions to the frontend layer.
