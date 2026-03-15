# TASK-038a — Fix Module Status Dot Colors & Alert Banner False Positive

## Goal

Fix two cosmetic/UX issues on the live production site: module status dots show red despite "Running" text, and the alert banner fires a false "WebSocket disconnected during market hours" warning outside market hours.

## Depends On

TASK-038

---

## Fix 1 — Module status dots show red despite "Running"

**Problem:** System Health page shows modules with green "running" text pills but red dots next to the module names. The overall status correctly shows "Healthy" with a green dot, but individual module dots are all red.

**Root cause:** The frontend component that renders module status dots maps the status string to a color. It likely checks for `"healthy"` or `"ok"` to show green, but the backend returns `"running"`. Since `"running"` doesn't match the green condition, it falls through to the default red.

**Fix:** In the System Health component (likely `features/system/PipelineStatus.tsx` or similar), find the status-to-color mapping and add `"running"` as a green status:

```typescript
// Before (likely):
const dotColor = status === 'healthy' || status === 'ok' ? 'bg-success' : 'bg-error';

// After:
const dotColor = ['healthy', 'ok', 'running'].includes(status) ? 'bg-success' : 
                 ['degraded', 'warning'].includes(status) ? 'bg-warning' : 'bg-error';
```

Or if it uses a map:
```typescript
const STATUS_COLORS: Record<string, string> = {
  healthy: 'bg-success',
  ok: 'bg-success',
  running: 'bg-success',
  degraded: 'bg-warning',
  unknown: 'bg-warning',
  warning: 'bg-warning',
  error: 'bg-error',
  stopped: 'bg-error',
  not_started: 'bg-text-tertiary',
};
```

## Fix 2 — Alert banner false positive outside market hours

**Problem:** Red alert banner shows "WebSocket disconnected during market hours" at 4 AM ET. Alpaca has 0 symbols (volume filter returns nothing after hours), so no WebSocket was started — this is correct behavior, not an alert.

**Root cause:** The alert evaluation engine creates an alert when the Alpaca WebSocket is disconnected, without checking:
- Whether the market is actually open
- Whether there are any symbols to subscribe to

**Fix approach — two options (pick whichever is simpler):**

**Option A — Fix the alert rule evaluation:**
In the alert evaluator (likely `backend/app/observability/alerts/evaluator.py` or `engine.py`), find the WebSocket disconnect check and add conditions:

```python
def _check_websocket_health(self):
    # Don't alert if market is closed
    if not self._is_market_hours():
        return None  # No alert
    
    # Don't alert if no symbols to subscribe
    ws_mgr = get_ws_manager()
    if ws_mgr and ws_mgr.get_total_symbols() == 0:
        return None  # No alert — no symbols expected
    
    # Only alert if we SHOULD be connected but aren't
    ...

def _is_market_hours(self):
    """US equity market: 9:30 AM - 4:00 PM ET, Mon-Fri"""
    from datetime import datetime
    import pytz
    et = datetime.now(pytz.timezone('US/Eastern'))
    if et.weekday() >= 5:  # Saturday/Sunday
        return False
    market_open = et.replace(hour=9, minute=30, second=0)
    market_close = et.replace(hour=16, minute=0, second=0)
    return market_open <= et <= market_close
```

**Option B — Auto-resolve the alert when conditions clear:**
If the alert is already stored in the database, add logic to auto-resolve it when market is closed or symbols = 0. The alert should have a `resolved_at` timestamp set.

**Option C — Delete the stale alert directly:**
If the alert is a one-time seed or was created during startup, clear it:
```python
# During startup, after market data init:
if not is_market_hours() or total_symbols == 0:
    await alert_service.resolve_all_by_rule("websocket_disconnect")
```

## Acceptance Criteria

| # | Criterion |
|---|-----------|
| AC1 | Module dots show green when status is "running" |
| AC2 | Module dots show yellow when status is "unknown" or "degraded" |
| AC3 | Module dots show red only for "error" or "stopped" |
| AC4 | Alert banner does not show WebSocket disconnect outside US market hours (Mon-Fri 9:30 AM - 4:00 PM ET) |
| AC5 | Alert banner does not show WebSocket disconnect when broker has 0 subscribed symbols |
| AC6 | No frontend crashes |
| AC7 | Nothing inside /studio modified (except BUILDER_OUTPUT.md) |

## Files to Modify

| File | What Changes |
|------|-------------|
| Frontend System Health component | Status-to-color mapping includes "running" as green |
| Backend alert evaluator | Market hours check + 0-symbol check before WebSocket alert |

