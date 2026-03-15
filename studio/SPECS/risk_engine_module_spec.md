# RISK_ENGINE_MODULE — Full Engineering Spec

## Purpose

Define the complete engineering specification for the risk engine module.
This spec must contain enough detail that a builder agent can implement
the entire module without asking engineering design questions.

## Module Ownership

The risk engine module owns:

- Risk evaluation of all signals
- Risk decision persistence
- Kill switch management (global and per-strategy)
- Risk configuration and limits
- Exposure calculations
- Drawdown monitoring
- Daily loss tracking
- Risk event logging

The risk engine module does NOT own:

- Signal creation (owned by strategy/signals module)
- Order execution (owned by paper trading module)
- Position persistence (owned by portfolio module)
- Portfolio accounting (owned by portfolio module)

---

## 1. Core Principle

**Default to rejection.** If the risk engine cannot determine whether a
signal is safe, it rejects. A missed trade is always better than a bad trade.
Every approval must be an explicit, affirmative decision — never a passthrough
because nothing checked it.

---

## 2. Pipeline Position

```
Signal (pending) → Risk Engine evaluates → Decision (approve/reject/modify)
                                         → Paper Trading Engine (if approved)
```

The risk engine consumes signals in "pending" status and produces
RiskDecision records. It updates the signal's status field and creates
a corresponding decision record.

---

## 3. Risk Check Sequence

When a signal arrives, the risk engine runs it through an ordered sequence
of checks. The order is from cheapest/fastest to most complex. Each check can:

- **Pass** — signal is fine on this dimension, continue to next check
- **Reject** — signal violates a rule, stop evaluation, reject with reason
- **Modify** — signal is acceptable if adjusted, continue with modification

If any check rejects, remaining checks are skipped. The rejection reason
comes from the first failing check.

### Check Order

```
1.  Global kill switch
2.  Strategy-level enable check
3.  Symbol tradability check
4.  Market hours check
5.  Duplicate order guard
6.  Position limit check
7.  Position sizing validation
8.  Per-symbol exposure limit
9.  Per-strategy exposure limit
10. Portfolio-level exposure limit
11. Drawdown check
12. Daily loss limit check
```

### Exit Signal Handling

Exit signals (including manual closes, safety exits, system exits) receive
lighter evaluation. The philosophy: **never prevent a position from being closed.**

Checks that APPLY to exit signals:
- Symbol tradability
- Market hours (if closed, queue for execution when market opens)

Checks that are SKIPPED for exit signals:
- Kill switch (exits are always allowed — reduce exposure, don't trap it)
- Position limits
- Position sizing
- All exposure limits
- Drawdown check
- Daily loss limit

---

## 4. Risk Checks — Detailed Specification

### Check 1 — Global Kill Switch

```
if global_kill_switch.is_active:
    if signal.signal_type in ["entry", "scale_in"]:
        reject("global_kill_switch", "Trading is globally halted")
    if signal.signal_type in ["exit", "scale_out"]:
        pass  # exits always allowed
```

The kill switch blocks new entries but always allows exits.

Can be triggered by:
- User clicking emergency stop in the UI
- Safety monitor detecting critical system failure
- Drawdown exceeding catastrophic threshold
- System-level failure detection

Kill switch state is persisted in the database (survives restarts).

### Check 2 — Strategy-Level Enable

```
if strategy.status != "enabled":
    reject("strategy_not_enabled", "Strategy is not in enabled state")
```

Catches race conditions where a strategy was disabled between signal
generation and risk evaluation.

Exception: signals with source="manual" or source="safety" or source="system"
bypass this check. These are not strategy-generated and should be processed
regardless of strategy state.

### Check 3 — Symbol Tradability

```
if symbol not on active watchlist:
    reject("symbol_not_tradable", "Symbol is not on active watchlist")
```

### Check 4 — Market Hours

```
if market is closed for this symbol's market:
    if signal.signal_type in ["exit", "scale_out"]:
        # queue for execution at market open, do not reject
        modify(queue_until_market_open=true)
    else:
        reject("market_closed", "Market is currently closed")
```

Equities: 9:30 AM - 4:00 PM ET weekdays (extended hours if configured)
Forex: Sunday 5:00 PM ET through Friday 5:00 PM ET

### Check 5 — Duplicate Order Guard

```
if pending or open order exists for same strategy + symbol + side:
    reject("duplicate_order", "Order already pending for this strategy and symbol")
```

Different from signal dedup. This checks the orders table, not the signals table.
Prevents two orders from the same intent if the pipeline is processing slowly.

### Check 6 — Position Limit Check

```
current_positions = count open positions for this strategy
max_positions = strategy.config.position_sizing.max_positions

if signal_type == "entry" and current_positions >= max_positions:
    reject("max_positions_reached",
           f"Strategy has {current_positions}/{max_positions} positions")
```

### Check 7 — Position Sizing Validation

```
requested_size = calculate_position_size(strategy.config, portfolio_state)
max_single_position = risk_config.max_position_size_percent / 100 * portfolio_equity

if requested_size <= 0:
    reject("invalid_size", "Calculated position size is zero or negative")

if requested_size > max_single_position:
    modify(reduce qty to max_single_position)
    # signal continues with reduced size
```

Position sizing methods:
- fixed_qty: exact share count from config
- fixed_dollar: dollar amount / current price
- percent_equity: equity * percent / current price
- risk_based: (equity * risk_percent) / (entry_price - stop_price)

The risk config max_position_size_percent is a ceiling that strategy
configs cannot exceed.

### Check 8 — Per-Symbol Exposure Limit

```
current_symbol_exposure = sum of all open position values in this symbol
                          (across ALL strategies)
max_symbol_exposure = risk_config.max_symbol_exposure_percent / 100 * portfolio_equity
proposed_total = current_symbol_exposure + proposed_position_value

if proposed_total > max_symbol_exposure:
    remaining_capacity = max_symbol_exposure - current_symbol_exposure
    min_viable = risk_config.min_position_value
    
    if remaining_capacity >= min_viable:
        modify(reduce size to remaining_capacity)
    else:
        reject("symbol_exposure_limit",
               f"Exposure to {symbol} would exceed {max_symbol_exposure_percent}%")
```

Prevents concentration risk. Multiple strategies buying AAPL are subject
to a combined cap.

### Check 9 — Per-Strategy Exposure Limit

```
current_strategy_exposure = sum of all open position values for this strategy
max_strategy_exposure = risk_config.max_strategy_exposure_percent / 100 * portfolio_equity

if current_strategy_exposure + proposed_value > max_strategy_exposure:
    reject("strategy_exposure_limit",
           f"Strategy exposure would exceed {max_strategy_exposure_percent}%")
```

Prevents one strategy from consuming all capital.

### Check 10 — Portfolio-Level Exposure Limit

```
total_exposure = sum of all open position values across all strategies
max_total = risk_config.max_total_exposure_percent / 100 * portfolio_equity

if total_exposure + proposed_value > max_total:
    reject("portfolio_exposure_limit",
           f"Total exposure would exceed {max_total_exposure_percent}%")
```

Overall leverage/exposure cap.

### Check 11 — Drawdown Check

```
current_drawdown = (peak_equity - current_equity) / peak_equity * 100

if current_drawdown >= risk_config.max_drawdown_percent:
    if signal_type in ["entry", "scale_in"]:
        reject("drawdown_limit",
               f"Drawdown at {current_drawdown:.1f}% exceeds {max_drawdown_percent}%")
    # exits and scale_out always pass
```

Only blocks entries. Never blocks exits.

### Check 12 — Daily Loss Limit

```
today_realized_loss = sum of realized losses today (all strategies)

if risk_config.max_daily_loss_amount:
    limit = risk_config.max_daily_loss_amount
elif risk_config.max_daily_loss_percent:
    limit = risk_config.max_daily_loss_percent / 100 * portfolio_equity

if today_realized_loss >= limit:
    if signal_type in ["entry", "scale_in"]:
        reject("daily_loss_limit",
               f"Daily loss ${today_realized_loss:.2f} exceeds limit")
    # exits always pass
```

Circuit breaker. Only blocks entries.

---

## 5. Risk Decision Data Model

```
RiskDecision:
  - id: UUID
  - signal_id: UUID (FK → Signal)
  - status: str (approved | rejected | modified)
  - checks_passed: list[str] (names of checks that passed before decision)
  - failed_check: str, nullable (name of check that caused rejection)
  - reason_code: str
  - reason_text: str
  - modifications_json: dict, nullable
      example: {
        "original_qty": 100,
        "approved_qty": 50,
        "modification_reason": "symbol_exposure_cap",
        "original_value": 18750.00,
        "approved_value": 9375.00
      }
  - portfolio_state_snapshot: dict
      example: {
        "equity": 100000.00,
        "cash": 58000.00,
        "total_exposure_percent": 42.0,
        "drawdown_percent": 3.2,
        "daily_pnl": -127.00,
        "peak_equity": 103300.00,
        "open_positions_count": 4
      }
  - ts: datetime (UTC)
  - created_at: datetime (UTC)

Indexes:
  INDEX (signal_id) UNIQUE
  INDEX (status, created_at)
  INDEX (reason_code)
  INDEX (ts)
```

### Field Details

**checks_passed:** Shows not just why something was rejected, but how far
it got in the evaluation. "Passed: kill_switch, strategy_enable, symbol_check,
duplicate_guard, position_limit. Failed: symbol_exposure_limit." This tells
you the signal was legitimate and was blocked by a specific risk rule.

**portfolio_state_snapshot:** Captures the portfolio's state at decision time.
Makes risk decisions fully reproducible: "given this portfolio state,
this signal would have been rejected because drawdown was at 8.5%."

**modifications_json:** If the signal was modified (quantity reduced, etc.),
records what changed and why. The paper trading engine uses the modified
values, not the original signal values.

---

## 6. Kill Switch

### Data Model

```
KillSwitch:
  - id: UUID
  - scope: str (global | strategy)
  - strategy_id: UUID, nullable (required if scope = strategy)
  - is_active: bool
  - activated_by: str (user | system | safety_monitor)
  - activated_at: datetime, nullable
  - deactivated_at: datetime, nullable
  - reason: str, nullable
  - updated_at: datetime

Indexes:
  INDEX (scope, is_active)
  INDEX (strategy_id, is_active) WHERE strategy_id IS NOT NULL
```

### Behavior

**Global kill switch:**
- Blocks ALL entry signals across ALL strategies
- Allows ALL exit signals (reduce exposure)
- Persists across restarts (stored in database)
- Requires explicit deactivation by user

**Strategy kill switch:**
- Blocks entry signals for one specific strategy
- Allows exits for that strategy
- Independent of global kill switch

### Activation Triggers

- User: clicks emergency stop button in UI
- System: drawdown exceeds catastrophic threshold (configurable)
- Safety monitor: detects critical system failure (all monitoring down)

### API

```
POST /api/v1/risk/kill-switch/activate
  body: { scope: "global" | "strategy", strategy_id?: UUID, reason?: str }

POST /api/v1/risk/kill-switch/deactivate
  body: { scope: "global" | "strategy", strategy_id?: UUID }

GET  /api/v1/risk/kill-switch/status
  returns: { global: bool, strategies: [{strategy_id, is_active}] }
```

---

## 7. Risk Configuration

### Data Model

```
RiskConfig:
  - id: UUID
  - max_position_size_percent: Decimal (default: 10.0)
  - max_symbol_exposure_percent: Decimal (default: 20.0)
  - max_strategy_exposure_percent: Decimal (default: 30.0)
  - max_total_exposure_percent: Decimal (default: 80.0)
  - max_drawdown_percent: Decimal (default: 10.0)
  - max_drawdown_catastrophic_percent: Decimal (default: 20.0)
      (auto-activates global kill switch)
  - max_daily_loss_percent: Decimal (default: 3.0)
  - max_daily_loss_amount: Decimal, nullable (absolute dollar override)
  - min_position_value: Decimal (default: 100.0)
  - updated_at: datetime
  - updated_by: str

Single row table — one active risk config for the system.
```

### Configuration Hierarchy

```
Risk config → sets maximum limits (portfolio-wide ceiling)
Strategy config → sets strategy-specific limits (cannot exceed risk limits)
Position overrides → set position-specific values (cannot exceed strategy limits)
```

If a strategy config requests position_size = 15% but risk config
max_position_size_percent = 10%, the risk engine caps at 10%.

### Editability

Risk config is editable through the admin UI without code changes
or redeployment. All changes are logged with who changed what and when.

```
RiskConfigAudit:
  - id: UUID
  - field_changed: str
  - old_value: str
  - new_value: str
  - changed_by: str
  - changed_at: datetime
```

---

## 8. Drawdown Monitoring

### Peak Equity Tracking

The risk engine maintains a running peak equity value:

```
peak_equity = max(peak_equity, current_equity)
current_drawdown = (peak_equity - current_equity) / peak_equity * 100
```

Peak equity is updated on every portfolio snapshot (when positions are
marked to market). It resets under specific conditions:

- **Never auto-resets.** A drawdown of 8% that recovers to 5% doesn't
  reset the peak. The peak is the historical high-water mark.
- **Manual reset:** Admin can reset peak equity through the UI (e.g., after
  adding new capital to the account). This is logged.

### Drawdown Thresholds

Three levels:

```
Warning:       drawdown >= max_drawdown_percent * 0.7 (default: 7%)
Breach:        drawdown >= max_drawdown_percent (default: 10%)
Catastrophic:  drawdown >= max_drawdown_catastrophic_percent (default: 20%)
```

**Warning:** Log event, surface in dashboard. Trading continues.

**Breach:** Reject all new entries. Exits still allowed. Alert user.
Trading resumes if drawdown recovers below the threshold.

**Catastrophic:** Activate global kill switch. All entries blocked.
Requires manual intervention to deactivate.

---

## 9. Daily Loss Tracking

### Calculation

```
daily_realized_loss = sum of (realized_pnl) for all fills today
                      where realized_pnl < 0
```

"Today" is defined by market timezone:
- Equities: midnight to midnight ET
- Forex: 5 PM ET to 5 PM ET (aligned with forex trading day)

### Reset

Daily loss counter resets at the start of each trading day.
The reset is automatic based on the clock, not manual.

### Thresholds

```
Warning: daily_loss >= max_daily_loss * 0.7
Breach:  daily_loss >= max_daily_loss
```

On breach: reject all new entries for the remainder of the trading day.
Exits still allowed. Alert user.

---

## 10. Exit Signal Risk Handling (Detailed)

Exit signals receive minimal risk evaluation to ensure positions can
always be closed:

```
Exit signal arrives:
  1. Check symbol tradability → if untradable, log warning (don't reject)
  2. Check market hours → if closed, queue for execution at open
  3. All other checks → SKIP
  4. Approve the exit signal

Risk decision for exits:
  status: "approved"
  checks_passed: ["exit_fast_path"]
  reason_code: "exit_approved"
  reason_text: "Exit signals receive expedited approval"
```

The only scenario where an exit is truly blocked is if the symbol has
been completely delisted or removed from the broker. Even then, the
system should queue the exit and alert the user rather than silently
rejecting it.

---

## 11. Risk-to-Paper-Trading Handoff

After the risk engine makes a decision:

**If approved:**
```
signal.status → "risk_approved"
RiskDecision created with status = "approved"
Paper trading engine picks up the approved signal and creates an order
```

**If modified:**
```
signal.status → "risk_modified"
RiskDecision created with status = "modified" and modifications_json
Paper trading engine uses the MODIFIED values from the risk decision,
not the original signal values
```

**If rejected:**
```
signal.status → "risk_rejected"
RiskDecision created with status = "rejected"
No further action. Signal is terminal.
```

The paper trading engine reads:
- signal.id, signal.symbol, signal.side, signal.signal_type
- risk_decision.status
- risk_decision.modifications_json (if modified)

---

## 12. Risk Dashboard View

```
Risk Overview:
  Kill Switch:        ● Inactive
  Portfolio Drawdown: 3.2% / 10.0% limit    ████░░░░░░
  Daily P&L:          -$127 / -$500 limit    ███░░░░░░░
  Total Exposure:     42% / 80% limit        █████░░░░░

  Per-Symbol Exposure:
    AAPL:   12% / 20%  ████████░░
    MSFT:    8% / 20%  █████░░░░░
    GOOGL:   6% / 20%  ████░░░░░░
    EUR_USD: 4% / 20%  ███░░░░░░░

  Per-Strategy Exposure:
    RSI + EMA Momentum:  18% / 30%  ██████░░░░
    Breakout Scanner:    12% / 30%  ████░░░░░░
    Forex Pairs:          4% / 30%  ██░░░░░░░░

  Recent Decisions:
    10:05  BUY AAPL    ✓ Approved    rsi_ema_momentum
    10:03  BUY MSFT    ✗ Rejected    symbol exposure limit
    09:45  SELL NVDA   ✓ Approved    manual close
    09:30  BUY GOOGL   ◐ Modified    qty 100→50 (strategy exposure cap)
```

Exposed via:
```
GET /api/v1/risk/overview
```

---

## 13. Risk Event Log

```
Events:
  risk.signal.approved           (signal_id, strategy, symbol)
  risk.signal.rejected           (signal_id, reason_code, reason_text)
  risk.signal.modified           (signal_id, modification details)
  risk.kill_switch.activated     (scope, activated_by, reason)
  risk.kill_switch.deactivated   (scope, deactivated_by)
  risk.drawdown.warning          (current_percent, threshold)
  risk.drawdown.breach           (current_percent, threshold)
  risk.drawdown.catastrophic     (current_percent, threshold, kill switch activated)
  risk.drawdown.recovered        (current_percent)
  risk.daily_loss.warning        (current_loss, limit)
  risk.daily_loss.breach         (current_loss, limit)
  risk.daily_loss.reset          (new trading day)
  risk.exposure.warning          (scope: symbol|strategy|portfolio, current, limit)
  risk.config.changed            (field, old_value, new_value, changed_by)
```

---

## 14. Folder Structure

```
backend/app/risk/
    __init__.py
    service.py              ← main risk evaluation orchestration
    models.py               ← SQLAlchemy models (RiskDecision, KillSwitch, RiskConfig)
    schemas.py              ← Pydantic request/response schemas
    router.py               ← API endpoints
    config.py               ← risk module configuration
    checks/
        __init__.py
        base.py             ← base check interface
        kill_switch.py      ← global and strategy kill switch check
        strategy_enable.py  ← strategy status check
        symbol.py           ← symbol tradability and market hours
        duplicate.py        ← duplicate order guard
        position_limit.py   ← max positions per strategy
        position_sizing.py  ← size validation and capping
        exposure.py         ← symbol, strategy, portfolio exposure limits
        drawdown.py         ← drawdown threshold check
        daily_loss.py       ← daily loss limit check
    monitoring/
        __init__.py
        drawdown.py         ← peak equity tracking, drawdown calculation
        daily_loss.py       ← daily loss accumulation and reset
        exposure.py         ← real-time exposure calculations
```

### Check Interface

Each check implements a standard interface:

```python
class RiskCheck:
    name: str               # e.g., "symbol_exposure_limit"
    applies_to_exits: bool  # whether this check runs for exit signals

    async def evaluate(self, signal, context) -> CheckResult:
        # Returns: pass, reject(reason), or modify(changes)
```

The risk service iterates through checks in order, passing a shared context
object that contains portfolio state, position data, and risk config.
This avoids redundant database queries across checks.

---

## 15. API Endpoints

```
# Risk Decisions
GET  /api/v1/risk/decisions                → list decisions with filters
                                             (signal_id, status, reason_code,
                                              date range, page, page_size)
GET  /api/v1/risk/decisions/:id            → decision detail

# Risk Overview
GET  /api/v1/risk/overview                 → current risk state
                                             (drawdown, exposure, daily loss,
                                              kill switch status)

# Kill Switch
POST /api/v1/risk/kill-switch/activate     → activate kill switch
POST /api/v1/risk/kill-switch/deactivate   → deactivate kill switch
GET  /api/v1/risk/kill-switch/status       → current kill switch state

# Risk Configuration
GET  /api/v1/risk/config                   → current risk configuration
PUT  /api/v1/risk/config                   → update risk configuration
GET  /api/v1/risk/config/audit             → config change history

# Exposure
GET  /api/v1/risk/exposure                 → current exposure breakdown
                                             (per symbol, per strategy, total)

# Drawdown
GET  /api/v1/risk/drawdown                 → current drawdown state
                                             (peak equity, current equity,
                                              drawdown percent, threshold status)
POST /api/v1/risk/drawdown/reset-peak      → manually reset peak equity (admin)
```

---

## 16. Configuration Variables

```
# Risk Limits (defaults, overridden by RiskConfig in database)
RISK_DEFAULT_MAX_POSITION_SIZE_PERCENT=10.0
RISK_DEFAULT_MAX_SYMBOL_EXPOSURE_PERCENT=20.0
RISK_DEFAULT_MAX_STRATEGY_EXPOSURE_PERCENT=30.0
RISK_DEFAULT_MAX_TOTAL_EXPOSURE_PERCENT=80.0
RISK_DEFAULT_MAX_DRAWDOWN_PERCENT=10.0
RISK_DEFAULT_MAX_DRAWDOWN_CATASTROPHIC_PERCENT=20.0
RISK_DEFAULT_MAX_DAILY_LOSS_PERCENT=3.0
RISK_DEFAULT_MIN_POSITION_VALUE=100.0

# Risk Evaluation
RISK_EVALUATION_TIMEOUT_SEC=5
RISK_CHECK_MARKET_HOURS=true
```

---

## 17. Database Tables Owned

| Table | Purpose |
|---|---|
| risk_decisions | All risk evaluation decisions with full context |
| risk_config | Current risk parameter configuration (single row) |
| risk_config_audit | Change history for risk configuration |
| kill_switches | Kill switch state (global and per-strategy) |

---

## Acceptance Criteria

This spec is accepted when:

- Core principle (default to rejection) is stated
- All 12 risk checks are specified with logic and ordering
- Exit signal handling (lighter evaluation, never block exits) is explicit
- Risk decision data model captures full evaluation context
- Kill switch behavior (blocks entries, allows exits) is defined
- Risk configuration is database-stored and editable
- Configuration hierarchy (risk > strategy > position) is documented
- Drawdown monitoring with three threshold levels is specified
- Daily loss tracking with auto-reset is specified
- Risk-to-paper-trading handoff contract is explicit
- Risk dashboard view is described
- All risk events are enumerated
- Check interface pattern is defined
- All API endpoints are listed
- All configuration variables are listed
- All database tables are enumerated
- A builder agent can implement this module without asking engineering design questions
