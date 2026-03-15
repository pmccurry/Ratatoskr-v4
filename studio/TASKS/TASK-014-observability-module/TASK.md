# TASK-014 — Observability Module Implementation

## Task Status
- Builder:    [ ] not started
- Validator:  [ ] not started
- Librarian:  [ ] not started

## Objective

Implement the complete observability module: the structured event log,
the event emission service, metrics collection, the alert system with
rules and notifications, and API endpoints for the telemetry dashboard.

After this task:
- All modules can emit structured audit events via a shared event service
- Events are queued, batched, and written to the database (non-blocking)
- The activity feed shows events with emoji-prefixed summaries
- System metrics are collected periodically (counters, gauges, histograms)
- Alert rules evaluate events and metrics, triggering notifications
- Notifications dispatch to dashboard banners, email, and webhook
- Built-in alert rules exist for critical conditions
- API endpoints support the telemetry dashboard, event browsing, and alert management
- Event retention cleanup runs daily

## Read First

1. /studio/STUDIO/PROJECT_STATE.md
2. /studio/STUDIO/DECISIONS.md
3. /studio/STUDIO/GLOSSARY.md
4. /studio/SPECS/observability_module_spec.md — PRIMARY SPEC, read completely
5. /studio/SPECS/cross_cutting_specs.md

## Constraints

- Do NOT modify business logic in other modules (no adding emit() calls yet —
  that's a wiring step for a future task or can be done incrementally)
- Do NOT create, modify, or delete anything inside /studio (except BUILDER_OUTPUT.md)
- Do NOT modify /CLAUDE.md
- Follow repository pattern and API conventions
- All timestamps UTC, all financial values Decimal where applicable
- Event emission must be non-blocking — modules must not slow down for logging

---

## Deliverables

### 1. Observability Models (backend/app/observability/models.py)

**AuditEvent:**
```
AuditEvent:
  - id: UUID (from BaseModel)
  - event_type: str (e.g., "signal.created", "risk.signal.rejected")
  - category: str (market_data | strategy | signal | risk |
                    paper_trading | portfolio | system | auth)
  - severity: str (debug | info | warning | error | critical)
  - source_module: str
  - entity_type: str, nullable
  - entity_id: UUID, nullable
  - strategy_id: UUID, nullable
  - symbol: str, nullable
  - summary: str (emoji-prefixed human-readable one-liner)
  - details_json: JSON, nullable
  - ts: datetime (when event occurred, UTC)
  - created_at (from BaseModel)

  Note: NO updated_at — events are immutable (append-only).

Indexes:
  INDEX (ts)
  INDEX (event_type, ts)
  INDEX (category, ts)
  INDEX (severity, ts)
  INDEX (strategy_id, ts) — partial WHERE strategy_id IS NOT NULL
  INDEX (symbol, ts) — partial WHERE symbol IS NOT NULL
  INDEX (entity_type, entity_id)
```

**MetricDatapoint:**
```
MetricDatapoint:
  - id: UUID (from BaseModel)
  - metric_name: str
  - metric_type: str (counter | gauge | histogram)
  - value: Numeric
  - labels_json: JSON, nullable (e.g., {"broker": "alpaca", "symbol": "AAPL"})
  - ts: datetime (UTC)
  - created_at (from BaseModel)

Indexes:
  INDEX (metric_name, ts)
  INDEX (ts)
```

**AlertRule:**
```
AlertRule:
  - id: UUID (from BaseModel)
  - name: str
  - description: str
  - category: str (system | trading | risk)
  - condition_type: str (event_match | metric_threshold | absence)
  - condition_config: JSON
  - severity: str (warning | error | critical)
  - enabled: bool (default true)
  - cooldown_seconds: int (default 300)
  - notification_channels: JSON (list of str: dashboard | email | webhook)
  - created_at, updated_at (from BaseModel)
```

**AlertInstance:**
```
AlertInstance:
  - id: UUID (from BaseModel)
  - rule_id: UUID (FK → alert_rules.id)
  - severity: str
  - summary: str
  - details_json: JSON
  - status: str (active | acknowledged | resolved)
  - triggered_at: datetime
  - acknowledged_at: datetime, nullable
  - acknowledged_by: str, nullable
  - resolved_at: datetime, nullable
  - notifications_sent: JSON (list of str)
  - created_at (from BaseModel)

Indexes:
  INDEX (status, triggered_at)
  INDEX (rule_id, triggered_at)
  INDEX (severity, status)
```

### 2. Event Emission Service (backend/app/observability/events/emitter.py)

```python
class EventEmitter:
    """Non-blocking event emission service.
    
    Modules call emit() which puts the event on an async queue.
    A background batch writer drains the queue and writes to the database.
    """
    
    def __init__(self, config: ObservabilityConfig):
        self._queue: asyncio.Queue = asyncio.Queue(
            maxsize=config.event_queue_max_size)
        self._config = config
        self._running = False
    
    async def emit(self, event_type: str, category: str, severity: str,
                   source_module: str, summary: str,
                   entity_type: str | None = None,
                   entity_id: UUID | None = None,
                   strategy_id: UUID | None = None,
                   symbol: str | None = None,
                   details: dict | None = None,
                   ts: datetime | None = None) -> None:
        """Emit an event (non-blocking).
        
        If queue is full: drop debug/info events, NEVER drop warning+.
        """
    
    async def start(self) -> None:
        """Start the batch writer background task."""
    
    async def stop(self) -> None:
        """Flush remaining events and stop."""
    
    async def _batch_writer(self) -> None:
        """Background task: drain queue, write in batches.
        
        Writes when batch_size reached OR interval elapsed.
        Uses EVENT_BATCH_WRITE_SIZE and EVENT_BATCH_WRITE_INTERVAL_SEC.
        """
    
    async def _handle_overflow(self, event_type: str, severity: str) -> bool:
        """Handle queue overflow.
        
        Returns True if event should be dropped.
        Drop order: debug first, then info. Never drop warning+.
        """
```

### 3. Event Repository (backend/app/observability/events/repository.py)

```python
class AuditEventRepository:
    async def create_batch(self, db, events: list[AuditEvent]) -> int
    async def get_by_id(self, db, event_id: UUID) -> AuditEvent | None
    async def get_filtered(self, db, category=None, severity=None,
                           event_type=None, strategy_id=None,
                           symbol=None, start=None, end=None,
                           page=1, page_size=50) -> tuple[list, int]
    async def get_recent(self, db, limit=50, category=None,
                         severity_gte=None) -> list[AuditEvent]
    async def cleanup_old(self, db, retention_days: int) -> int
```

### 4. Metrics Collector (backend/app/observability/metrics/collector.py)

```python
class MetricsCollector:
    """Periodically collects system metrics from all modules.
    
    Runs every METRICS_COLLECTION_INTERVAL_SEC. Queries each module's
    health/status interfaces and records metric datapoints.
    """
    
    async def start(self) -> None:
        """Start the collection loop."""
    
    async def stop(self) -> None:
        """Stop the collection loop."""
    
    async def collect_cycle(self, db) -> int:
        """Run one collection cycle. Returns count of datapoints recorded.
        
        Collects from:
        - Market data: connection status, stale symbols, queue depth, bar write rate
        - Strategies: enabled count, evaluation duration, error count
        - Signals: pending count, expired count, approval rate
        - Risk: rejection rate, drawdown, exposure, daily loss
        - Paper trading: order count, fill count, consumer lag
        - Portfolio: equity, cash, open positions count
        - System: uptime, event queue depth
        """
    
    async def record(self, db, metric_name: str, metric_type: str,
                     value: Decimal, labels: dict | None = None) -> None:
        """Record a single metric datapoint."""
```

### 5. Metrics Repository (backend/app/observability/metrics/repository.py)

```python
class MetricDatapointRepository:
    async def create(self, db, datapoint: MetricDatapoint) -> MetricDatapoint
    async def create_batch(self, db, datapoints: list[MetricDatapoint]) -> int
    async def get_timeseries(self, db, metric_name: str,
                             start: datetime | None = None,
                             end: datetime | None = None,
                             labels: dict | None = None,
                             resolution: str = "1m"  # 1m | 5m | 1h | 1d
                             ) -> list[MetricDatapoint]
    async def get_latest(self, db, metric_name: str,
                         labels: dict | None = None) -> MetricDatapoint | None
    async def list_metric_names(self, db) -> list[str]
    async def cleanup_old(self, db, retention_days: int) -> int
```

### 6. Alert Engine (backend/app/observability/alerts/engine.py)

```python
class AlertEngine:
    """Evaluates alert rules against events and metrics.
    
    Runs every ALERT_EVALUATION_INTERVAL_SEC.
    """
    
    async def start(self) -> None:
        """Start the evaluation loop."""
    
    async def stop(self) -> None:
        """Stop the evaluation loop."""
    
    async def evaluate_cycle(self, db) -> int:
        """Run one evaluation cycle.
        
        For each enabled rule:
        1. Evaluate condition (event_match, metric_threshold, or absence)
        2. If triggered and no active instance exists (or cooldown passed):
           → Create AlertInstance (status=active)
           → Dispatch notifications
        3. If previously active but condition cleared:
           → Auto-resolve the instance
        
        Returns count of new alerts triggered.
        """
    
    async def _evaluate_event_match(self, db, config: dict) -> bool:
        """Check if a matching event occurred recently."""
    
    async def _evaluate_metric_threshold(self, db, config: dict) -> bool:
        """Check if a metric exceeds threshold for duration."""
    
    async def _evaluate_absence(self, db, config: dict) -> bool:
        """Check if an expected event is missing."""
```

### 7. Alert Repository (backend/app/observability/alerts/repository.py)

```python
class AlertRuleRepository:
    async def get_all(self, db) -> list[AlertRule]
    async def get_enabled(self, db) -> list[AlertRule]
    async def get_by_id(self, db, rule_id: UUID) -> AlertRule | None
    async def create(self, db, rule: AlertRule) -> AlertRule
    async def update(self, db, rule: AlertRule) -> AlertRule

class AlertInstanceRepository:
    async def create(self, db, instance: AlertInstance) -> AlertInstance
    async def get_active(self, db) -> list[AlertInstance]
    async def get_filtered(self, db, status=None, severity=None,
                           start=None, end=None,
                           page=1, page_size=20) -> tuple[list, int]
    async def get_by_id(self, db, instance_id: UUID) -> AlertInstance | None
    async def acknowledge(self, db, instance_id: UUID, by: str) -> AlertInstance
    async def resolve(self, db, instance_id: UUID) -> AlertInstance
    async def get_active_for_rule(self, db, rule_id: UUID) -> AlertInstance | None
```

### 8. Notification Dispatcher (backend/app/observability/alerts/notifications.py)

```python
class NotificationDispatcher:
    """Sends alert notifications through configured channels."""
    
    async def dispatch(self, alert: AlertInstance, rule: AlertRule) -> list[str]:
        """Send notifications on all configured channels.
        
        Returns list of channels successfully notified.
        """
    
    async def _send_dashboard(self, alert: AlertInstance) -> bool:
        """Dashboard notifications are implicit (stored in DB, read by frontend).
        Always returns True."""
    
    async def _send_email(self, alert: AlertInstance, config: dict) -> bool:
        """Send email notification.
        
        For MVP: log the email content (actual SMTP integration deferred).
        Returns True if email would have been sent.
        """
    
    async def _send_webhook(self, alert: AlertInstance, config: dict) -> bool:
        """Send webhook notification via httpx POST.
        
        Payload: {severity, alert_name, summary, details, triggered_at}
        Returns True if webhook responded 2xx.
        """
```

### 9. Built-In Alert Rules Seeder (backend/app/observability/alerts/seed.py)

```python
async def seed_alert_rules(db) -> int:
    """Create built-in alert rules if they don't exist.
    
    Critical:
    - Global kill switch activated (event_match)
    - Safety monitor failure ≥3 consecutive (event_match)
    - Catastrophic drawdown (event_match)
    - WebSocket disconnected >5 min during market hours (absence)
    
    Error:
    - Strategy auto-paused (event_match)
    - Broker API failure with fallback (event_match)
    - Daily loss limit breached (event_match)
    - Drawdown limit breached (event_match)
    - Queue backpressure critical >80% (metric_threshold)
    
    Warning:
    - Symbols stale >5 for >2 min (metric_threshold)
    - Drawdown approaching limit >70% (metric_threshold)
    - Daily loss approaching limit >70% (metric_threshold)
    - Signal expired (event_match)
    - Queue elevated >20% (metric_threshold)
    - Forex pool at capacity (event_match)
    
    Returns count of rules created.
    """
```

### 10. Observability Schemas (backend/app/observability/schemas.py)

camelCase aliases, envelope format.

```python
class AuditEventResponse(BaseModel):
    id, event_type, category, severity, source_module, entity_type,
    entity_id, strategy_id, symbol, summary, details_json, ts, created_at

class MetricDatapointResponse(BaseModel):
    metric_name, metric_type, value, labels_json, ts

class AlertRuleResponse(BaseModel):
    id, name, description, category, condition_type, condition_config,
    severity, enabled, cooldown_seconds, notification_channels, created_at

class AlertInstanceResponse(BaseModel):
    id, rule_id, severity, summary, details_json, status, triggered_at,
    acknowledged_at, acknowledged_by, resolved_at, notifications_sent

class UpdateAlertRuleRequest(BaseModel):
    enabled: bool | None = None
    cooldown_seconds: int | None = None
    severity: str | None = None

class SystemHealthResponse(BaseModel):
    overall_status: str  # healthy | degraded | unhealthy
    uptime_seconds: int
    modules: dict  # per-module status
    pipeline: dict  # pipeline stage statuses

class PipelineStatusResponse(BaseModel):
    market_data: dict
    strategies: dict
    signals: dict
    risk: dict
    paper_trading: dict
    portfolio: dict
```

### 11. Observability Errors (backend/app/observability/errors.py)

```python
class EventNotFoundError(DomainError):
    # OBSERVABILITY_EVENT_NOT_FOUND, 404

class AlertRuleNotFoundError(DomainError):
    # OBSERVABILITY_ALERT_RULE_NOT_FOUND, 404

class AlertInstanceNotFoundError(DomainError):
    # OBSERVABILITY_ALERT_NOT_FOUND, 404
```

Register in common/errors.py.

### 12. Observability Config (backend/app/observability/config.py)

```python
class ObservabilityConfig:
    def __init__(self):
        s = get_settings()
        self.event_queue_max_size = s.event_queue_max_size
        self.event_batch_write_size = s.event_batch_write_size
        self.event_batch_write_interval = s.event_batch_write_interval_sec
        self.event_retention_days = s.event_retention_days
        self.metrics_collection_interval = s.metrics_collection_interval_sec
        self.metrics_retention_days = s.metrics_retention_days
        self.alert_evaluation_interval = s.alert_evaluation_interval_sec
        self.alert_email_enabled = s.alert_email_enabled
        self.alert_email_recipients = s.alert_email_recipients
        self.alert_email_min_severity = s.alert_email_min_severity
        self.alert_webhook_enabled = s.alert_webhook_enabled
        self.alert_webhook_url = s.alert_webhook_url
        self.alert_webhook_min_severity = s.alert_webhook_min_severity
        self.log_level = s.log_level
        self.log_format = s.log_format
```

### 13. Observability Service (backend/app/observability/service.py)

```python
class ObservabilityService:
    """Main service for observability queries and management."""
    
    # Events
    async def get_events(self, db, **filters) -> tuple[list, int]
    async def get_recent_events(self, db, limit=50, **filters) -> list
    async def get_event(self, db, event_id: UUID) -> AuditEvent
    
    # System Health
    async def get_system_health(self) -> dict
    async def get_pipeline_status(self) -> dict
    
    # Metrics
    async def list_metrics(self, db) -> list[str]
    async def get_metric_timeseries(self, db, metric_name, **filters) -> list
    
    # Alerts
    async def get_alerts(self, db, **filters) -> tuple[list, int]
    async def get_active_alerts(self, db) -> list[AlertInstance]
    async def acknowledge_alert(self, db, alert_id: UUID, by: str) -> AlertInstance
    async def get_alert_rules(self, db) -> list[AlertRule]
    async def update_alert_rule(self, db, rule_id: UUID, updates: dict) -> AlertRule
```

### 14. Observability Router (backend/app/observability/router.py)

Replace the empty stub.

```
# Events / Activity Feed
GET  /api/v1/observability/events            → events with filters (paginated)
GET  /api/v1/observability/events/recent     → last N events (activity feed)
GET  /api/v1/observability/events/:id        → event detail

# System Health
GET  /api/v1/observability/health            → overall system health
GET  /api/v1/observability/health/pipeline   → per-module pipeline status

# Metrics
GET  /api/v1/observability/metrics           → list available metric names
GET  /api/v1/observability/metrics/:name     → metric time series

# Alerts
GET  /api/v1/observability/alerts            → alert instances (filtered)
GET  /api/v1/observability/alerts/active     → active alerts only
POST /api/v1/observability/alerts/:id/ack    → acknowledge an alert
GET  /api/v1/observability/alert-rules       → list alert rules
PUT  /api/v1/observability/alert-rules/:id   → update rule (admin only)
```

All require auth. Rule updates require admin.
All responses use {"data": ...} envelope with camelCase.

### 15. Event Retention Cleanup

Add to the event emitter or a separate daily job:

```python
async def cleanup_expired_events(self, db) -> int:
    """Delete events older than EVENT_RETENTION_DAYS. Returns count deleted."""

async def cleanup_expired_metrics(self, db) -> int:
    """Delete metric datapoints older than METRICS_RETENTION_DAYS."""
```

### 16. Observability Startup (backend/app/observability/startup.py)

```python
async def start_observability() -> None:
    """Initialize observability module.
    
    1. Load config
    2. Create EventEmitter and start batch writer
    3. Create MetricsCollector and start collection loop
    4. Create AlertEngine and start evaluation loop
    5. Seed built-in alert rules
    """

async def stop_observability() -> None:
    """Stop all background tasks (emitter, collector, alert engine)."""

def get_event_emitter() -> EventEmitter:
    """Get the event emitter for other modules to use."""
```

### 17. Register in main.py

Add observability startup/shutdown. It should start FIRST (before other
modules) so events can be emitted during their startup:

```python
await start_observability()  # first — other modules need the emitter
await start_market_data(db)
await start_strategies()
# ...
# Shutdown in reverse
await stop_market_data()
# ...
await stop_observability()  # last — capture shutdown events
```

### 18. Application Logging Configuration (backend/app/observability/logging/config.py)

```python
def configure_logging(config: ObservabilityConfig) -> None:
    """Configure Python logging for the application.
    
    - JSON format for production (LOG_FORMAT=json)
    - Human-readable for development (LOG_FORMAT=text)
    - Level from LOG_LEVEL setting
    - Output to stdout (container-friendly)
    
    This is separate from the audit event system.
    Python logging = operational/debug output.
    Audit events = business-level events for the dashboard.
    """
```

### 19. Alembic Migration

Create migration for all four tables (audit_events, metric_datapoints,
alert_rules, alert_instances).

---

## Acceptance Criteria

### Models and Migration
1. AuditEvent model exists with all fields and seven indexes
2. AuditEvent has no updated_at (immutable, append-only)
3. MetricDatapoint model exists with all fields
4. AlertRule model exists with condition_config as JSON
5. AlertInstance model exists with lifecycle tracking fields
6. Alembic migration creates all four tables and applies cleanly

### Event Emission
7. EventEmitter.emit() is non-blocking (puts on async queue)
8. Batch writer drains queue and writes in configurable batch sizes
9. Batch writer flushes at batch_size OR interval (whichever first)
10. Queue overflow drops debug first, then info, NEVER drops warning+
11. Queue overflow logs a meta-event about dropped events

### Event Storage and Query
12. Events are immutable (no update or delete via service)
13. Event queries support filtering by category, severity, event_type, strategy_id, symbol, date range
14. Recent events query supports limit and severity filter
15. Event retention cleanup deletes old events based on config

### Metrics Collection
16. MetricsCollector runs periodically at configured interval
17. Collector gathers metrics from multiple module interfaces
18. Metric datapoints stored with name, type, value, labels, timestamp
19. Metric time series queryable by name, date range, labels
20. Metric retention cleanup deletes old datapoints

### Alert Engine
21. Alert engine evaluates enabled rules at configured interval
22. event_match condition type triggers on matching events
23. metric_threshold condition type triggers when value exceeds threshold for duration
24. absence condition type triggers when expected event doesn't occur in window
25. Cooldown prevents re-alerting within configured window
26. Auto-resolve clears alerts when triggering condition no longer met

### Alert Management
27. AlertInstance created with status=active when rule triggers
28. Acknowledgment sets acknowledged_at and acknowledged_by
29. Resolution sets resolved_at
30. Active alerts queryable for dashboard banners

### Notifications
31. Dashboard notifications stored in DB (read by frontend)
32. Webhook notifications sent via httpx POST with correct payload
33. Email notifications logged for MVP (actual SMTP deferred)
34. Notification channels configurable per rule

### Built-In Rules
35. All critical built-in rules seeded on startup (~4 rules)
36. All error built-in rules seeded (~5 rules)
37. All warning built-in rules seeded (~6 rules)
38. Rules are created only if they don't already exist (idempotent seed)

### API
39. GET /observability/events returns filtered, paginated events
40. GET /observability/events/recent returns activity feed
41. GET /observability/events/:id returns event detail
42. GET /observability/health returns system health summary
43. GET /observability/health/pipeline returns per-module status
44. GET /observability/metrics lists available metrics
45. GET /observability/metrics/:name returns time series
46. GET /observability/alerts returns filtered alert instances
47. GET /observability/alerts/active returns active alerts
48. POST /observability/alerts/:id/ack acknowledges an alert
49. GET /observability/alert-rules returns all rules
50. PUT /observability/alert-rules/:id updates a rule (admin only)
51. All responses use {"data": ...} envelope with camelCase

### Integration
52. Observability starts FIRST in main.py lifespan
53. Observability stops LAST in main.py lifespan
54. get_event_emitter() returns the emitter singleton for other modules
55. Application logging configured (JSON/text format, stdout)

### General
56. ObservabilityConfig loads all settings
57. Error classes exist and registered in common/errors.py
58. Nothing inside /studio modified (except BUILDER_OUTPUT.md)

---

## Required Output

When complete, write BUILDER_OUTPUT.md to this task's directory:
/studio/TASKS/TASK-014-observability/BUILDER_OUTPUT.md

Use the template from /studio/AGENTS/builder/OUTPUT_TEMPLATE.md
Fill in EVERY section. Leave nothing blank.
