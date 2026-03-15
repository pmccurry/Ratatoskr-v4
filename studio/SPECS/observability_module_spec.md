# OBSERVABILITY_MODULE — Full Engineering Spec

## Purpose

Define the complete engineering specification for the observability module.
This spec must contain enough detail that a builder agent can implement
the entire module without asking engineering design questions.

## Module Ownership

The observability module owns:

- Unified structured event log (audit events from all modules)
- Event emission service (used by all modules)
- System metrics collection and storage
- Alert rules, evaluation, and notification
- Notification channel dispatching (dashboard, email, webhook)
- Application logging configuration
- System health aggregation
- Pipeline latency tracking
- Background job status tracking

The observability module does NOT own:

- Business logic in any other module
- Event definitions (each module defines its own events)
- Market data health checks (owned by market_data, reported here)
- Risk monitoring logic (owned by risk, reported here)

---

## 1. Design Philosophy

### Two Audiences, One System

The observability module serves both:

- **Operator/trader:** watching strategies, signals, trades, PnL in real-time
- **Developer/admin:** watching infrastructure health, latency, errors, throughput

Both views read from the same event and metric stores, filtered and
presented differently.

### Three Layers

```
Layer 1 — Structured Event Log    (what happened)
Layer 2 — System Metrics          (how the system is performing)
Layer 3 — Alerts and Notifications (what needs attention)
```

---

## 2. Layer 1 — Structured Event Log

### Purpose

Every business-level event from every module flows into a single unified
event store. This is the foundation for the activity feed, audit trail,
and alert evaluation.

### AuditEvent Data Model

```
AuditEvent:
  - id: UUID
  - event_type: str (e.g., "signal.created", "risk.signal.rejected")
  - category: str (market_data | strategy | signal | risk |
                    paper_trading | portfolio | system | auth)
  - severity: str (debug | info | warning | error | critical)
  - source_module: str (which backend module emitted this)
  - entity_type: str, nullable (strategy | signal | order | position | etc.)
  - entity_id: UUID, nullable (the specific entity this relates to)
  - strategy_id: UUID, nullable (if event is strategy-related)
  - symbol: str, nullable (if event is symbol-related)
  - summary: str (human-readable one-line description with emoji prefix)
  - details_json: dict, nullable (structured payload with full context)
  - ts: datetime (when the event occurred, UTC)
  - created_at: datetime

Indexes:
  INDEX (ts)
  INDEX (event_type, ts)
  INDEX (category, ts)
  INDEX (severity, ts)
  INDEX (strategy_id, ts) WHERE strategy_id IS NOT NULL
  INDEX (symbol, ts) WHERE symbol IS NOT NULL
  INDEX (entity_type, entity_id)
```

### Severity Levels

```
debug:     Verbose operational detail (bar written, indicator computed).
           Not shown in dashboard by default.

info:      Normal operational events (evaluation completed, signal created).
           Shown in activity feed.

warning:   Something needs attention but isn't broken
           (symbol stale, queue elevated, position override created).

error:     Something failed but the system continues
           (strategy evaluation error, broker API failure with fallback).

critical:  Something requires immediate intervention
           (kill switch activated, safety monitor failure, catastrophic drawdown).
```

### Summary Field Convention

Every event summary is human-readable and prefixed with an emoji
for at-a-glance scanning:

```
📊  Strategy evaluation events
✅  Approval / success events
❌  Rejection / failure events
📝  Order events
💰  Fill / money events
📂  Position events
📸  Snapshot events
🔴  Critical alerts
🟠  Error alerts
🟡  Warning alerts
🔌  Connection events
⏱️  Timing / latency events
💵  Dividend events
⚙️  Configuration changes
🛑  Kill switch events
```

### Details JSON Examples

**Signal created:**
```json
{
  "signal_id": "abc-123",
  "strategy_key": "rsi_ema_momentum",
  "strategy_version": "1.3.0",
  "symbol": "AAPL",
  "side": "buy",
  "signal_type": "entry",
  "confidence": 0.85,
  "indicators": {
    "rsi_14": 28.5,
    "ema_200": 185.10,
    "adx_14": 31.2
  },
  "evaluation_duration_ms": 45
}
```

**Risk rejection:**
```json
{
  "signal_id": "abc-123",
  "decision_id": "def-456",
  "reason_code": "symbol_exposure_limit",
  "reason_text": "Exposure to AAPL would exceed 20%",
  "checks_passed": ["kill_switch", "strategy_enable", "symbol_check",
                     "duplicate_guard", "position_limit"],
  "failed_check": "symbol_exposure",
  "current_exposure_percent": 18.5,
  "limit_percent": 20.0
}
```

### Event Append-Only Rule

Events are never updated or deleted. This is an immutable audit trail.

### Event Retention

```
EVENT_RETENTION_DAYS=365
```

Events older than retention period are pruned by a daily cleanup job.

---

## 3. Event Emission Service

### How Modules Emit Events

All modules use a shared event emitter:

```python
await event_service.emit(
    event_type="signal.created",
    category="signal",
    severity="info",
    entity_type="signal",
    entity_id=signal.id,
    strategy_id=signal.strategy_id,
    symbol=signal.symbol,
    summary="📊 Strategy 'RSI Momentum': BUY AAPL signal generated",
    details={
        "signal_id": str(signal.id),
        "confidence": signal.confidence,
        "indicators": payload_snapshot
    }
)
```

### Non-Blocking Emission

The emit call is non-blocking. Events are queued in an async in-memory
queue and written to the database in batches by a background task.

```
Module calls emit() → event goes to async queue → batch writer → DB
```

Queue configuration:
```
EVENT_QUEUE_MAX_SIZE=50000
EVENT_BATCH_WRITE_SIZE=100
EVENT_BATCH_WRITE_INTERVAL_SEC=5
```

### Queue Overflow Behavior

If the event queue fills:
- Debug-level events are dropped first
- Info-level events dropped next
- Warning, error, and critical events are NEVER dropped
- A meta-event is logged: "Event queue overflow: N debug events dropped"

---

## 4. Complete Event Catalog

### Market Data Events

```
market_data.connection.established     info      🔌 {broker} WebSocket connected
market_data.connection.lost            error     🔌 {broker} WebSocket disconnected: {reason}
market_data.connection.reconnecting    warning   🔌 {broker} reconnecting (attempt {n})
market_data.connection.recovered       info      🔌 {broker} reconnected (gap: {duration})
market_data.symbol.stale               warning   🟡 {symbol} data stale for >{threshold}s
market_data.symbol.recovered           info      ✅ {symbol} data recovered
market_data.queue.backpressure_warning warning   🟡 Bar write queue at {percent}% capacity
market_data.queue.backpressure_critical error    🟠 Bar write queue at {percent}% — risk of data loss
market_data.write.error                error     🟠 Bar write failed: {error}
market_data.aggregation.failed         error     🟠 Aggregation failed for {symbol} {timeframe}
market_data.health.degraded            warning   🟡 Market data health degraded: {reason}
market_data.health.unhealthy           error     🟠 Market data unhealthy: {reason}
market_data.health.recovered           info      ✅ Market data health recovered
market_data.backfill.started           info      ⏱️ Backfill started: {symbols_count} symbols
market_data.backfill.completed         info      ✅ Backfill completed: {bars_fetched} bars
market_data.backfill.failed            error     🟠 Backfill failed for {symbol}: {error}
```

### Strategy Events

```
strategy.evaluation.completed          info      📊 {strategy}: {symbols} symbols, {signals} signals
strategy.evaluation.skipped            info      📊 {strategy} skipped: {reason}
strategy.evaluation.error              error     🟠 {strategy} evaluation error: {error}
strategy.auto_paused                   error     🟠 {strategy} auto-paused: {consecutive_errors} errors
strategy.enabled                       info      ✅ {strategy} enabled
strategy.disabled                      info      ⚙️ {strategy} disabled
strategy.paused                        info      ⚙️ {strategy} paused
strategy.resumed                       info      ✅ {strategy} resumed
strategy.config_changed                info      ⚙️ {strategy} config updated: v{old} → v{new}
strategy.safety_monitor.active         warning   🟡 Safety monitor active for {strategy}: {positions} positions
strategy.safety_monitor.exit           info      🛑 Safety monitor exit: {symbol} ({reason})
```

### Signal Events

```
signal.created                         info      📊 {strategy}: {side} {symbol} signal generated
signal.approved                        info      ✅ Signal approved: {side} {symbol}
signal.rejected                        warning   ❌ Signal rejected: {side} {symbol} ({reason})
signal.modified                        info      ⚙️ Signal modified: {side} {symbol} ({modification})
signal.expired                         warning   🟡 Signal expired: {side} {symbol} (pending too long)
signal.canceled                        info      ❌ Signal canceled: {side} {symbol} ({reason})
signal.deduplicated                    debug     📊 Signal deduplicated: {side} {symbol}
```

### Risk Events

```
risk.signal.approved                   info      ✅ Risk approved: {side} {symbol} ({strategy})
risk.signal.rejected                   warning   ❌ Risk rejected: {side} {symbol} ({reason_code})
risk.signal.modified                   info      ⚙️ Risk modified: {side} {symbol} ({modification})
risk.kill_switch.activated             critical  🛑 Kill switch activated: {scope} by {actor}: {reason}
risk.kill_switch.deactivated           info      ✅ Kill switch deactivated: {scope} by {actor}
risk.drawdown.warning                  warning   🟡 Drawdown at {percent}% (limit: {limit}%)
risk.drawdown.breach                   error     🟠 Drawdown breach: {percent}% exceeds {limit}%
risk.drawdown.catastrophic             critical  🔴 Catastrophic drawdown: {percent}% — kill switch activated
risk.drawdown.recovered                info      ✅ Drawdown recovered to {percent}%
risk.daily_loss.warning                warning   🟡 Daily loss ${amount} approaching limit ${limit}
risk.daily_loss.breach                 error     🟠 Daily loss limit breached: ${amount}
risk.daily_loss.reset                  info      ✅ Daily loss counter reset (new trading day)
risk.exposure.warning                  warning   🟡 {scope} exposure at {percent}% (limit: {limit}%)
risk.config.changed                    info      ⚙️ Risk config updated: {field} {old} → {new}
```

### Paper Trading Events

```
paper_trading.order.created            info      📝 Order: {side} {qty} {symbol} @ {type}
paper_trading.order.accepted           info      📝 Order accepted: {order_id}
paper_trading.order.filled             info      💰 Fill: {side} {qty} {symbol} @ {price} (fee: ${fee})
paper_trading.order.rejected           warning   ❌ Order rejected: {symbol} ({reason})
paper_trading.order.canceled           info      ❌ Order canceled: {symbol} ({reason})
paper_trading.fill.processed           info      💰 Fill processed: portfolio updated
paper_trading.cash.insufficient        warning   🟡 Insufficient cash: need ${need}, have ${have}
paper_trading.broker.api_error         error     🟠 Broker API error: {broker} — {error}
paper_trading.forex_pool.allocated     info      📂 Forex account {n} allocated: {symbol} {side} ({strategy})
paper_trading.forex_pool.released      info      📂 Forex account {n} released: {symbol} ({strategy})
paper_trading.forex_pool.blocked       warning   🟡 No forex account available: {symbol} ({strategy})
paper_trading.shadow.fill_created      info      👻 Shadow fill: {side} {symbol} ({strategy})
paper_trading.shadow.position_closed   info      👻 Shadow position closed: {symbol} PnL ${pnl}
```

### Portfolio Events

```
portfolio.position.opened              info      📂 Position opened: {side} {qty} {symbol} @ {price} ({strategy})
portfolio.position.scaled_in           info      📂 Position scaled in: +{qty} {symbol}, avg {new_avg}
portfolio.position.scaled_out          info      📂 Position scaled out: -{qty} {symbol}, realized ${pnl}
portfolio.position.closed              info      📂 Position closed: {symbol} realized ${pnl} ({reason})
portfolio.pnl.realized                 info      💰 Realized PnL: ${pnl} on {symbol} ({strategy})
portfolio.equity.snapshot              debug     📸 Equity: ${equity}, cash: ${cash}, drawdown: {dd}%
portfolio.equity.new_peak              info      📸 New equity peak: ${peak}
portfolio.equity.peak_reset            warning   ⚙️ Peak equity manually reset to ${peak} by {user}
portfolio.cash.adjusted                info      💰 Cash adjusted: {account} ${old} → ${new} ({reason})
portfolio.dividend.eligible            info      💵 Dividend eligible: {symbol} ${amount} ({shares} shares)
portfolio.dividend.paid                info      💵 Dividend paid: ${amount} for {symbol} → cash credited
portfolio.split.adjusted               info      ⚙️ Split adjusted: {symbol} {ratio} ({positions} positions)
portfolio.option.expired               info      📂 Option expired: {symbol} intrinsic ${value}, PnL ${pnl}
portfolio.mark_to_market.completed     debug     ⏱️ MTM completed: {count} positions in {duration}ms
portfolio.mark_to_market.stale         warning   🟡 MTM: {count} positions with stale prices
portfolio.corporate_action.fetched     debug     ⚙️ Corporate actions fetched: {count} events found
```

### System Events

```
system.startup                         info      ✅ System started
system.shutdown                        info      ⚙️ System shutting down
system.ready                           info      ✅ All modules ready — system operational
system.error                           error     🟠 System error: {error}
```

---

## 5. Layer 2 — System Metrics

### Purpose

Numerical summaries tracking system health over time. Counters, gauges,
and histograms collected periodically or on increment.

### Metric Data Model

```
MetricDatapoint:
  - id: UUID
  - metric_name: str
  - metric_type: str (counter | gauge | histogram)
  - value: Decimal
  - labels_json: dict, nullable (e.g., {"broker": "alpaca", "strategy": "rsi_momentum"})
  - ts: datetime
  - created_at: datetime

Indexes:
  INDEX (metric_name, ts)
  INDEX (metric_name, labels_json, ts)
```

### Collection

- Gauges: sampled every METRICS_COLLECTION_INTERVAL_SEC (default: 60)
- Counters: incremented on each occurrence, snapshot stored each interval
- Histograms: percentiles calculated each interval from accumulated values

### Metric Catalog

**Market Data:**
```
market_data.bars_received_total            counter    (labels: broker)
market_data.bars_received_per_minute       gauge      (labels: broker)
market_data.bars_written_total             counter
market_data.bars_write_errors_total        counter
market_data.aggregations_completed_total   counter
market_data.websocket_uptime_seconds       gauge      (labels: broker)
market_data.websocket_reconnections_total  counter    (labels: broker)
market_data.queue_depth                    gauge
market_data.stale_symbols_count            gauge
market_data.backfill_progress_percent      gauge
```

**Strategy:**
```
strategy.evaluations_total                 counter    (labels: strategy_key)
strategy.evaluations_per_minute            gauge
strategy.evaluation_duration_ms            histogram  (labels: strategy_key)
strategy.signals_emitted_total             counter    (labels: strategy_key)
strategy.evaluations_skipped_total         counter    (labels: reason)
strategy.errors_total                      counter    (labels: strategy_key)
strategy.active_count                      gauge
```

**Signal:**
```
signal.created_total                       counter    (labels: source)
signal.approved_total                      counter
signal.rejected_total                      counter    (labels: reason_code)
signal.modified_total                      counter
signal.expired_total                       counter
signal.deduplicated_total                  counter
signal.pending_count                       gauge
signal.time_to_decision_ms                 histogram
```

**Risk:**
```
risk.decisions_total                       counter    (labels: status)
risk.rejections_by_reason                  counter    (labels: reason_code)
risk.evaluation_duration_ms                histogram
risk.current_drawdown_percent              gauge
risk.current_daily_loss                    gauge
risk.current_total_exposure_percent        gauge
risk.kill_switch_activations_total         counter
```

**Paper Trading:**
```
paper_trading.orders_total                 counter    (labels: status, market)
paper_trading.fills_total                  counter    (labels: market)
paper_trading.avg_slippage_bps             histogram  (labels: market)
paper_trading.total_fees                   counter
paper_trading.forex_pool_utilization       gauge
paper_trading.shadow_fills_total           counter
paper_trading.broker_api_errors_total      counter
```

**Portfolio:**
```
portfolio.equity                           gauge
portfolio.cash_balance                     gauge
portfolio.open_positions_count             gauge
portfolio.unrealized_pnl                   gauge
portfolio.realized_pnl_today               gauge
portfolio.dividend_income_total            counter
portfolio.mark_to_market_duration_ms       histogram
```

**System:**
```
system.api_requests_total                  counter    (labels: endpoint, method)
system.api_request_duration_ms             histogram  (labels: endpoint)
system.api_errors_total                    counter    (labels: endpoint, status_code)
system.database_query_duration_ms          histogram
system.background_jobs_running             gauge
system.uptime_seconds                      gauge
```

### Metric Retention

```
METRICS_COLLECTION_INTERVAL_SEC=60
METRICS_RETENTION_DAYS=90
```

Datapoints older than retention period are pruned daily.
Daily aggregates (min, max, avg per metric per day) are kept indefinitely.

---

## 6. Layer 3 — Alerts and Notifications

### Alert Rule Model

```
AlertRule:
  - id: UUID
  - name: str
  - description: str
  - category: str (system | trading | risk)
  - condition_type: str (event_match | metric_threshold | absence)
  - condition_config: dict
  - severity: str (warning | error | critical)
  - enabled: bool
  - cooldown_seconds: int (don't re-alert within this window)
  - notification_channels: list[str] (dashboard | email | webhook)
  - created_at: datetime
  - updated_at: datetime
```

### Condition Types

**event_match** — triggers when a specific event occurs:

```json
{
  "event_type": "risk.kill_switch.activated",
  "severity_gte": "critical"
}
```

**metric_threshold** — triggers when a metric crosses a value:

```json
{
  "metric_name": "market_data.stale_symbols_count",
  "operator": "greater_than",
  "value": 10,
  "duration_seconds": 120
}
```

`duration_seconds` prevents flapping — condition must persist before alerting.

**absence** — triggers when an expected event doesn't occur:

```json
{
  "event_type": "strategy.evaluation.completed",
  "expected_interval_seconds": 120,
  "market_hours_only": true
}
```

Catches silent failures.

### Built-In Alert Rules

**Critical (immediate attention):**
```
- Global kill switch activated
- Safety monitor failure (3+ consecutive failures)
- Catastrophic drawdown reached
- WebSocket disconnected 5+ minutes during market hours
```

**Error (action needed):**
```
- Strategy auto-paused due to errors
- Broker API failure (fallback in use)
- Daily loss limit breached
- Drawdown limit breached
- Queue backpressure critical (>80%)
```

**Warning (awareness):**
```
- Symbols stale (>5 symbols for >2 minutes)
- Drawdown approaching limit (>70% of threshold)
- Daily loss approaching limit (>70% of threshold)
- Signal expired (pipeline may be slow)
- Queue backpressure elevated (>20%)
- Forex account pool at capacity for a pair
```

### Alert Instance Model

```
AlertInstance:
  - id: UUID
  - rule_id: UUID (FK → AlertRule)
  - severity: str
  - summary: str
  - details_json: dict
  - status: str (active | acknowledged | resolved)
  - triggered_at: datetime
  - acknowledged_at: datetime, nullable
  - acknowledged_by: str, nullable
  - resolved_at: datetime, nullable
  - notifications_sent: list[str]
  - created_at: datetime

Indexes:
  INDEX (status, triggered_at)
  INDEX (rule_id, triggered_at)
  INDEX (severity, status)
```

### Alert Lifecycle

```
active → acknowledged → resolved
      → resolved (auto-resolved when condition clears)
```

Users acknowledge alerts (dismisses banner, keeps record).
System auto-resolves when the triggering condition clears.

### Alert Evaluation

```
ALERT_EVALUATION_INTERVAL_SEC=30
```

Every 30 seconds, the alert engine:
1. Evaluates all enabled rules against current events and metrics
2. For newly triggered rules: create AlertInstance, dispatch notifications
3. For previously active alerts where condition cleared: auto-resolve
4. Respect cooldown_seconds (don't re-alert within window)

---

## 7. Notification Channels

### Dashboard (always active)

Alerts appear as banners at the top of the dashboard, color-coded:

```
🔴 CRITICAL: Global kill switch activated by system — drawdown at 21.3%
🟠 ERROR: Strategy "Scalper 5m" auto-paused after 5 consecutive errors
🟡 WARNING: 12 symbols have stale data (>2 minutes)
```

Critical alerts are persistent (require acknowledgment to dismiss).
Warnings auto-dismiss when resolved.

### Email (configurable)

```
ALERT_EMAIL_ENABLED=false
ALERT_EMAIL_RECIPIENTS=user@example.com
ALERT_EMAIL_MIN_SEVERITY=error
```

### Webhook (configurable)

For Slack, Discord, PagerDuty, etc.

```
ALERT_WEBHOOK_ENABLED=false
ALERT_WEBHOOK_URL=https://hooks.slack.com/services/...
ALERT_WEBHOOK_MIN_SEVERITY=error
```

Payload format:

```json
{
  "severity": "error",
  "alert_name": "Strategy Auto-Paused",
  "summary": "🟠 Strategy 'Scalper 5m' auto-paused after 5 consecutive errors",
  "details": { "strategy_key": "scalper_5m", "error_count": 5, "last_error": "..." },
  "triggered_at": "2025-03-10T14:30:00Z",
  "dashboard_url": "https://your-app.com/alerts/abc-123"
}
```

---

## 8. Dashboard Views — Telemetry Board

### System Health Overview

```
System Status: ● Healthy (all systems operational)
Uptime: 4d 12h 33m

Pipeline Status:
  Market Data:     ● Connected (Alpaca: 312 symbols, OANDA: 28 pairs)
  Strategy Runner: ● Active (8 strategies enabled, last cycle: 12s ago)
  Risk Engine:     ● Active (last evaluation: 3s ago)
  Paper Trading:   ● Active (last fill: 47m ago)
  Portfolio:       ● Updated (last MTM: 23s ago)

Throughput (last hour):
  Bars received:     18,720
  Bars written:      18,718 (2 rejected)
  Evaluations:       487
  Signals emitted:   12
  Risk approved:     9
  Risk rejected:     3
  Orders filled:     9
```

### Pipeline Latency

```
Pipeline Timing (last hour averages):
  Bar received → DB write:           45ms
  Strategy evaluation:               62ms
  Signal → Risk decision:            8ms
  Risk → Order fill:                 12ms
  Fill → Position update:            5ms
  Total signal-to-fill:              87ms
```

### Error and Warning Feed

```
Recent Issues:
  14:30  🟡 3 symbols stale for >2 min (TSLA, AMZN, META) — recovered 14:32
  13:15  🟠 Broker API timeout on order submit — fallback to simulation
  09:31  🟡 Backfill gap detected: AAPL 1m bars missing 09:28-09:30
```

### Background Jobs

```
Scheduled Jobs:
  Universe Filter:      last 09:00, next 09:00 tomorrow    ● success
  Corporate Actions:    last 08:00, next 08:00 tomorrow    ● success
  Signal Expiry Sweep:  last 14:30, next 14:31             ● running
  Mark-to-Market:       last 14:30, next 14:31             ● running
  Portfolio Snapshot:    last 14:25, next 14:30             ● success
  Metric Collection:    last 14:30, next 14:31             ● running
  Event Cleanup:        last 03:00, next 03:00 tomorrow    ● success
  Metric Pruning:       last 03:15, next 03:15 tomorrow    ● success
```

### Database Stats (admin)

```
Table Sizes:
  ohlcv_bars:           2.4M rows  (1.2 GB)
  audit_events:         847K rows  (420 MB)
  signals:              12.3K rows (8 MB)
  paper_orders:         9.1K rows  (5 MB)
  portfolio_snapshots:  28K rows   (12 MB)
  metric_datapoints:    340K rows  (85 MB)

Query Performance:
  Avg query time:        4.2ms
  Slow queries (>100ms): 3 in last hour
```

### Activity Feed (Real-Time)

```
Activity Feed (live):
  14:30:12  📊 RSI Momentum evaluated: 5 symbols, 0 signals
  14:30:11  📊 London Breakout evaluated: 3 pairs, 1 signal (BUY EUR_USD)
  14:30:11  ✅ Risk approved: BUY EUR_USD (London Breakout)
  14:30:11  📝 Order created: BUY 10,000 EUR_USD @ market
  14:30:12  💰 Fill: BUY 10,000 EUR_USD @ 1.0923 (fee: $0, slip: 0.2bps)
  14:30:12  📂 Position opened: EUR_USD long 10,000 (London Breakout)
  14:30:05  📊 Div Capture evaluated: 8 symbols, 0 signals
  14:25:00  📸 Portfolio snapshot: equity $103,847, drawdown 1.2%

Filters:
  Category: [All] [Market Data] [Strategy] [Signals] [Risk] [Trading] [Portfolio]
  Strategy: [All] [RSI Momentum] [London Breakout] [Div Capture]
  Severity: [All] [Info+] [Warning+] [Error+]
  Symbol:   [All] [AAPL] [EUR_USD] [...]
```

The feed reads from audit_events with WebSocket or polling for real-time
updates to connected dashboard clients.

---

## 9. Application Logging (Separate from Audit Events)

### Distinction

- **Audit events:** Business-level records for operators and traders.
  "Signal created," "position closed." Stored in database. Queryable via API.
- **Application logs:** Technical records for developers.
  "HTTP request received," "database query executed," "exception caught."
  Written to stdout for container log collection.

### Structured JSON Format

```json
{
  "timestamp": "2025-03-10T14:30:12.345Z",
  "level": "INFO",
  "module": "market_data.streams.manager",
  "message": "Bar received and queued",
  "context": {
    "symbol": "AAPL",
    "timeframe": "1m",
    "queue_depth": 12
  },
  "request_id": "req-abc-123"
}
```

### Rules

- All logs use structured JSON format
- No print() statements in production code
- Every log includes module path, timestamp, and relevant context
- API request logs include request_id for correlation

### Log Levels

```
DEBUG:    every bar received, every indicator computed
INFO:     server started, job completed, normal operations
WARNING:  something unusual but not broken
ERROR:    something failed, system continues
CRITICAL: something requires immediate attention
```

### Configuration

```
LOG_LEVEL=INFO
LOG_FORMAT=json       (json | text — text is easier for local dev)
```

### Request Logging Middleware

FastAPI middleware logs every API request:

```json
{
  "timestamp": "...",
  "level": "INFO",
  "module": "observability.middleware",
  "message": "API request",
  "context": {
    "method": "GET",
    "path": "/api/v1/portfolio/positions",
    "status_code": 200,
    "duration_ms": 12,
    "request_id": "req-abc-123"
  }
}
```

---

## 10. Folder Structure

```
backend/app/observability/
    __init__.py
    service.py              ← event emission and query service
    models.py               ← SQLAlchemy models
    schemas.py              ← Pydantic request/response schemas
    router.py               ← API endpoints
    config.py               ← observability configuration
    events/
        __init__.py
        emitter.py          ← async event emission with queue
        categories.py       ← event type constants and severity mapping
    metrics/
        __init__.py
        collector.py        ← periodic metric collection
        registry.py         ← metric definitions and registration
        store.py            ← metric persistence and query
    alerts/
        __init__.py
        engine.py           ← alert rule evaluation loop
        rules.py            ← built-in alert rule definitions
        notifications.py    ← channel dispatching (dashboard, email, webhook)
    logging/
        __init__.py
        config.py           ← structured logging setup
        middleware.py       ← request logging middleware for FastAPI
```

---

## 11. API Endpoints

```
# Audit Events / Activity Feed
GET  /api/v1/observability/events            → events with filters
                                               (category, severity, event_type,
                                                strategy_id, symbol, date range,
                                                page, page_size)
GET  /api/v1/observability/events/recent     → last N events (activity feed)
                                               (limit, category, severity filters)
GET  /api/v1/observability/events/:id        → event detail with full payload

# System Health
GET  /api/v1/observability/health            → overall system health
GET  /api/v1/observability/health/pipeline   → per-module pipeline status
GET  /api/v1/observability/health/latency    → pipeline latency metrics

# Metrics
GET  /api/v1/observability/metrics           → list available metrics
GET  /api/v1/observability/metrics/:name     → metric time series
                                               (labels, date range, resolution)

# Alerts
GET  /api/v1/observability/alerts            → alert instances with filters
                                               (status, severity, date range)
GET  /api/v1/observability/alerts/active     → currently active alerts
POST /api/v1/observability/alerts/:id/ack    → acknowledge an alert
GET  /api/v1/observability/alert-rules       → list alert rules
PUT  /api/v1/observability/alert-rules/:id   → update rule (enable/disable, threshold)

# Background Jobs
GET  /api/v1/observability/jobs              → scheduled job statuses

# Admin
GET  /api/v1/observability/database/stats    → table sizes, query performance
```

---

## 12. Configuration Variables

```
# Event Logging
EVENT_QUEUE_MAX_SIZE=50000
EVENT_BATCH_WRITE_SIZE=100
EVENT_BATCH_WRITE_INTERVAL_SEC=5
EVENT_RETENTION_DAYS=365

# Metrics
METRICS_COLLECTION_INTERVAL_SEC=60
METRICS_RETENTION_DAYS=90

# Alerts
ALERT_EVALUATION_INTERVAL_SEC=30
ALERT_EMAIL_ENABLED=false
ALERT_EMAIL_RECIPIENTS=
ALERT_EMAIL_MIN_SEVERITY=error
ALERT_WEBHOOK_ENABLED=false
ALERT_WEBHOOK_URL=
ALERT_WEBHOOK_MIN_SEVERITY=error

# Application Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

---

## 13. Database Tables Owned

| Table | Purpose |
|---|---|
| audit_events | All business-level events from all modules |
| metric_datapoints | Time-series metric values |
| alert_rules | Alert condition definitions |
| alert_instances | Alert trigger history and acknowledgment |

---

## Acceptance Criteria

This spec is accepted when:

- Three-layer architecture (events, metrics, alerts) is defined
- AuditEvent data model with all fields and indexes is specified
- Event emission service with async queue and overflow behavior is specified
- Complete event catalog (~60 event types across all modules) is documented
- Summary field convention with emoji prefixes is defined
- All system metrics are enumerated with types and labels
- Metric storage and retention model is specified
- Alert rule model with three condition types is defined
- Built-in alert rules are enumerated by severity
- Alert lifecycle (active, acknowledged, resolved) is specified
- All three notification channels (dashboard, email, webhook) are specified
- Telemetry dashboard views are described in detail
- Activity feed with filtering is specified
- Application logging (separate from audit events) is specified
- Request logging middleware is specified
- All API endpoints are listed
- All configuration variables are listed
- All database tables are enumerated
- A builder agent can implement this module without asking engineering design questions
