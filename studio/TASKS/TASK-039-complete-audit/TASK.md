# TASK-039 — Complete Audit Event Emissions

## Goal

Add all remaining event emissions defined in the observability spec event catalog. TASK-034 added 4 emission points (signal.created, signal.status_changed, risk.evaluation.completed, paper_trading.order.filled). This task adds the remaining ~30 emissions so the audit trail is complete and the Activity Feed shows real system activity.

## Depends On

TASK-038a

## Scope

**In scope:**
- Strategy module event emissions (evaluation, lifecycle, safety monitor)
- Risk module event emissions (kill switch, drawdown, daily loss, exposure warnings)
- Paper trading event emissions (order created/rejected, forex pool, shadow tracking)
- Portfolio module event emissions (position lifecycle, cash, PnL, dividends, splits, MTM)
- Signal module additions (deduplicated event)

**Out of scope:**
- New API endpoints
- Frontend changes (Activity Feed already reads from audit_events)
- Test creation
- Observability system metrics (counters, gauges — separate from audit events)

---

## Event Emission Pattern

All emissions follow the pattern established in TASK-034:

```python
try:
    from app.observability.events import get_event_emitter
    await get_event_emitter().emit(
        event_type="module.event_name",
        category="module_category",
        severity="info",
        entity_id=str(entity.id),
        entity_type="entity_name",
        summary="📊 Human-readable summary with {details}",
        payload={"key": "value", ...},
        user_id=str(user_id) if user_id else None,
    )
except Exception:
    pass  # Event emission never disrupts trading pipeline
```

Every `emit()` call is wrapped in `try/except Exception: pass`. Event failures never block the trading pipeline.

---

## Deliverables

### D1 — Strategy Module Events

**File:** `backend/app/strategies/runner.py` (or wherever strategy evaluation happens)

| Event Type | When | Severity | Summary |
|-----------|------|----------|---------|
| `strategy.evaluation.completed` | After each strategy evaluation cycle completes | info | `📊 {strategy_name}: {symbol_count} symbols, {signal_count} signals` |
| `strategy.evaluation.skipped` | When evaluation is skipped (market closed, data stale, etc.) | info | `📊 {strategy_name} skipped: {reason}` |
| `strategy.evaluation.error` | When evaluation raises an exception | error | `🟠 {strategy_name} evaluation error: {error}` |

**File:** `backend/app/strategies/service.py` (lifecycle transitions)

| Event Type | When | Severity | Summary |
|-----------|------|----------|---------|
| `strategy.enabled` | Strategy enabled (draft→enabled or re-enabled) | info | `✅ {strategy_name} enabled` |
| `strategy.disabled` | Strategy disabled | info | `⚙️ {strategy_name} disabled` |
| `strategy.paused` | Strategy paused (manually or by system) | info | `⚙️ {strategy_name} paused` |
| `strategy.resumed` | Strategy resumed from pause | info | `✅ {strategy_name} resumed` |
| `strategy.config_changed` | Strategy config updated (new version) | info | `⚙️ {strategy_name} config updated: v{old} → v{new}` |
| `strategy.auto_paused` | Auto-paused due to consecutive errors | error | `🟠 {strategy_name} auto-paused: {error_count} errors` |

**File:** `backend/app/strategies/safety_monitor.py` (if it exists)

| Event Type | When | Severity | Summary |
|-----------|------|----------|---------|
| `strategy.safety_monitor.exit` | Safety monitor triggers an exit signal | info | `🛑 Safety monitor exit: {symbol} ({reason})` |

### D2 — Risk Module Events

**File:** `backend/app/risk/service.py` (kill switch and monitoring)

| Event Type | When | Severity | Summary |
|-----------|------|----------|---------|
| `risk.kill_switch.activated` | Kill switch activated (manual or automatic) | critical | `🛑 Kill switch activated: {scope} by {actor}: {reason}` |
| `risk.kill_switch.deactivated` | Kill switch deactivated | info | `✅ Kill switch deactivated: {scope} by {actor}` |

**File:** `backend/app/risk/monitoring/drawdown.py` (or wherever drawdown is checked)

| Event Type | When | Severity | Summary |
|-----------|------|----------|---------|
| `risk.drawdown.warning` | Drawdown approaches limit (e.g., >75% of max) | warning | `🟡 Drawdown at {percent}% (limit: {limit}%)` |
| `risk.drawdown.breach` | Drawdown exceeds max limit | error | `🟠 Drawdown breach: {percent}% exceeds {limit}%` |
| `risk.drawdown.catastrophic` | Drawdown exceeds catastrophic threshold → kill switch | critical | `🔴 Catastrophic drawdown: {percent}% — kill switch activated` |

**File:** `backend/app/risk/monitoring/daily_loss.py` (or equivalent)

| Event Type | When | Severity | Summary |
|-----------|------|----------|---------|
| `risk.daily_loss.breach` | Daily loss limit exceeded | error | `🟠 Daily loss limit breached: ${amount}` |

**File:** `backend/app/risk/router.py` (config changes)

| Event Type | When | Severity | Summary |
|-----------|------|----------|---------|
| `risk.config.changed` | Risk configuration updated via API | info | `⚙️ Risk config updated: {field} {old} → {new}` |

### D3 — Paper Trading Events

**File:** `backend/app/paper_trading/service.py` (order lifecycle)

| Event Type | When | Severity | Summary |
|-----------|------|----------|---------|
| `paper_trading.order.created` | New order submitted to executor | info | `📝 Order: {side} {qty} {symbol} @ {type}` |
| `paper_trading.order.rejected` | Order rejected by executor (insufficient cash, no price, etc.) | warning | `❌ Order rejected: {symbol} ({reason})` |

**File:** `backend/app/paper_trading/forex_pool/pool_manager.py`

| Event Type | When | Severity | Summary |
|-----------|------|----------|---------|
| `paper_trading.forex_pool.allocated` | Forex account allocated to a strategy/pair | info | `📂 Forex account {n} allocated: {symbol} {side} ({strategy})` |
| `paper_trading.forex_pool.released` | Forex account released after position close | info | `📂 Forex account {n} released: {symbol} ({strategy})` |
| `paper_trading.forex_pool.blocked` | No account available for pair — signal blocked | warning | `🟡 No forex account available: {symbol} ({strategy})` |

**File:** `backend/app/paper_trading/shadow/tracker.py`

| Event Type | When | Severity | Summary |
|-----------|------|----------|---------|
| `paper_trading.shadow.fill_created` | Shadow fill created for contention-blocked signal | info | `👻 Shadow fill: {side} {symbol} ({strategy})` |
| `paper_trading.shadow.position_closed` | Shadow position closed | info | `👻 Shadow position closed: {symbol} PnL ${pnl}` |

### D4 — Portfolio Events

**File:** `backend/app/portfolio/fill_processor.py` (or wherever fills update positions)

| Event Type | When | Severity | Summary |
|-----------|------|----------|---------|
| `portfolio.position.opened` | New position created from fill | info | `📂 Position opened: {side} {qty} {symbol} @ {price} ({strategy})` |
| `portfolio.position.scaled_in` | Existing position scaled into | info | `📂 Position scaled in: +{qty} {symbol}, avg {new_avg}` |
| `portfolio.position.scaled_out` | Partial close of position | info | `📂 Position scaled out: -{qty} {symbol}, realized ${pnl}` |
| `portfolio.position.closed` | Full close of position | info | `📂 Position closed: {symbol} realized ${pnl}` |
| `portfolio.pnl.realized` | Realized PnL recorded | info | `💰 Realized PnL: ${pnl} on {symbol} ({strategy})` |

**File:** `backend/app/portfolio/cash_manager.py` (or equivalent)

| Event Type | When | Severity | Summary |
|-----------|------|----------|---------|
| `portfolio.cash.adjusted` | Cash balance changes (fill, dividend, manual) | info | `💰 Cash adjusted: ${old} → ${new} ({reason})` |

**File:** `backend/app/portfolio/dividends.py` (or equivalent)

| Event Type | When | Severity | Summary |
|-----------|------|----------|---------|
| `portfolio.dividend.paid` | Dividend payment processed | info | `💵 Dividend paid: ${amount} for {symbol} → cash credited` |

**File:** `backend/app/portfolio/splits.py` (or equivalent)

| Event Type | When | Severity | Summary |
|-----------|------|----------|---------|
| `portfolio.split.adjusted` | Stock split applied to positions | info | `⚙️ Split adjusted: {symbol} {ratio} ({position_count} positions)` |

**File:** `backend/app/portfolio/options_lifecycle.py`

| Event Type | When | Severity | Summary |
|-----------|------|----------|---------|
| `portfolio.option.expired` | Options contract expired | info | `📂 Option expired: {symbol} intrinsic ${value}, PnL ${pnl}` |

### D5 — Signal Module Addition

**File:** `backend/app/signals/service.py`

| Event Type | When | Severity | Summary |
|-----------|------|----------|---------|
| `signal.deduplicated` | Signal rejected by dedup logic | debug | `📊 Signal deduplicated: {side} {symbol}` |

---

## Acceptance Criteria

| # | Criterion |
|---|-----------|
| AC1 | Strategy evaluation events emitted (completed, skipped, error) |
| AC2 | Strategy lifecycle events emitted (enabled, disabled, paused, resumed, config_changed, auto_paused) |
| AC3 | Kill switch activation/deactivation events emitted with actor and reason |
| AC4 | Drawdown warning/breach events emitted |
| AC5 | Paper trading order.created and order.rejected events emitted |
| AC6 | Forex pool allocated/released/blocked events emitted |
| AC7 | Shadow tracking fill_created and position_closed events emitted |
| AC8 | Portfolio position opened/scaled_in/scaled_out/closed events emitted |
| AC9 | Portfolio cash.adjusted events emitted |
| AC10 | Portfolio dividend.paid and split.adjusted events emitted |
| AC11 | Signal.deduplicated event emitted at debug severity |
| AC12 | All emissions wrapped in try/except (never disrupt trading pipeline) |
| AC13 | All emissions use correct emoji prefixes per observability spec |
| AC14 | All emissions include entity_id and entity_type for trace linkage |
| AC15 | No frontend code modified |
| AC16 | Nothing inside /studio modified (except BUILDER_OUTPUT.md) |

---

## Files to Modify

| File | Events Added |
|------|-------------|
| `backend/app/strategies/runner.py` | evaluation.completed, evaluation.skipped, evaluation.error |
| `backend/app/strategies/service.py` | enabled, disabled, paused, resumed, config_changed, auto_paused |
| `backend/app/strategies/safety_monitor.py` | safety_monitor.exit (if file exists) |
| `backend/app/risk/service.py` | kill_switch.activated, kill_switch.deactivated |
| `backend/app/risk/monitoring/drawdown.py` | drawdown.warning, drawdown.breach, drawdown.catastrophic |
| `backend/app/risk/monitoring/daily_loss.py` | daily_loss.breach |
| `backend/app/risk/router.py` | config.changed |
| `backend/app/paper_trading/service.py` | order.created, order.rejected |
| `backend/app/paper_trading/forex_pool/pool_manager.py` | forex_pool.allocated, forex_pool.released, forex_pool.blocked |
| `backend/app/paper_trading/shadow/tracker.py` | shadow.fill_created, shadow.position_closed |
| `backend/app/portfolio/fill_processor.py` | position.opened, position.scaled_in, position.scaled_out, position.closed, pnl.realized |
| `backend/app/portfolio/cash_manager.py` | cash.adjusted |
| `backend/app/portfolio/dividends.py` | dividend.paid |
| `backend/app/portfolio/splits.py` | split.adjusted |
| `backend/app/portfolio/options_lifecycle.py` | option.expired |
| `backend/app/signals/service.py` | signal.deduplicated |

## Files NOT to Touch

- Frontend code
- Studio files
- Test files
- Infrastructure/Docker files

---

## Builder Notes

- **Follow the exact pattern from TASK-034.** The 4 existing emissions (signal.created, signal.status_changed, risk.evaluation.completed, paper_trading.order.filled) use `get_event_emitter().emit()` with try/except. Copy this pattern exactly.
- **Find the right insertion point.** Each event should be emitted AFTER the action succeeds, not before. For example, emit `portfolio.position.opened` after the position is actually created in the database, not before.
- **entity_id linkage matters.** Use the correct entity ID so the signal trace endpoint can chain events together:
  - Strategy events: `entity_id=str(strategy.id)`, `entity_type="strategy"`
  - Risk events: `entity_id=str(decision.id)` or `str(signal.id)`, `entity_type="risk_decision"` or `"signal"`
  - Order events: `entity_id=str(order.id)`, `entity_type="paper_order"`
  - Position events: `entity_id=str(position.id)`, `entity_type="position"`
  - Fill events: `entity_id=str(fill.id)`, `entity_type="fill"`
- **Some files may not exist exactly as named.** If `safety_monitor.py` or `daily_loss.py` don't exist, find where that logic lives and add the emission there. Document actual file paths in BUILDER_OUTPUT.md.
- **Debug-level events** (signal.deduplicated, portfolio.equity.snapshot, portfolio.mtm.completed) are optional — include them if the emission point is obvious, skip if it requires significant refactoring.
- **Don't refactor to add emissions.** If a function doesn't have access to the event emitter or the entity ID, pass them through or use the existing import pattern. Don't restructure code.

## References

- observability_module_spec.md §2 — Complete Event Catalog (all event types with emoji, severity, payload)
- TASK-034 BUILDER_OUTPUT.md — Existing emission pattern and entity_id linkage
