# TASK-034 — Audit Trail Verification & Trade Reconciliation

## Goal

Verify that every trade decision is fully traceable through the event system: signal → risk decision → order → fill → position. Add a reconciliation endpoint that compares internal state against broker state. After this task, every trade action has a complete, immutable audit chain, and operators can verify internal records match broker records.

## Depends On

TASK-032 (Alpaca pipeline working), TASK-033 (OANDA pipeline working)

## Scope

**In scope:**
- Verify the audit event chain is complete for the full signal-to-position pipeline
- Verify risk decisions log the check that rejected/approved with reasons
- Verify order and fill events are logged with all required fields
- Verify events are immutable (never updated or deleted)
- Add a reconciliation endpoint that compares internal positions/fills against broker state
- Add a signal trace endpoint that returns the full event chain for a signal
- Verify the activity feed on the dashboard pulls from the audit trail

**Out of scope:**
- Frontend changes (UI already reads from the API)
- New event types beyond what's in the observability spec
- Performance optimization of event queries

---

## Deliverables

### D1 — Verify complete audit event chain

Walk through a real trade (or simulated one) and verify every step produces an audit event.

**Expected event chain for a successful entry:**

```
1. strategy.evaluation.completed     — strategy runner evaluated, signal conditions met
2. signal.created                    — entry signal created with full payload snapshot
3. signal.status_changed (pending → risk_approved) — risk evaluation passed all checks
4. risk.evaluation.completed         — risk decision with checks passed/failed/modified
5. paper_trading.order.created       — order submitted to executor
6. paper_trading.order.filled        — fill received with price, qty, fees
7. signal.status_changed (risk_approved → order_filled) — signal fully processed
8. portfolio.position.opened         — new position created
9. portfolio.cash.updated            — cash debited
```

**For a rejected signal:**

```
1. strategy.evaluation.completed     — signal conditions met
2. signal.created                    — signal created
3. signal.status_changed (pending → risk_rejected) — risk rejected
4. risk.evaluation.completed         — decision with rejection reason and check name
```

**Verification steps:**
1. Ensure a trade flows through the pipeline (use Alpaca with real data, or manually seed a signal)
2. Query `GET /api/v1/observability/events?category=signal&sortBy=createdAt&sortOrder=asc`
3. Query `GET /api/v1/observability/events?category=risk`
4. Query `GET /api/v1/observability/events?category=paper_trading`
5. Query `GET /api/v1/observability/events?category=portfolio`
6. Verify the chain is complete — no gaps, no missing events
7. Verify each event has: `timestamp`, `category`, `event_type`, `severity`, `payload` with relevant IDs (signal_id, order_id, fill_id, position_id)

**If events are missing:** Find where the event emission was skipped and add it. Check:
- `signal_service.py` — emits signal.created and signal.status_changed
- `risk_service.py` — emits risk.evaluation.completed
- `paper_trading/service.py` — emits order.created and order.filled
- `portfolio/fill_processor.py` — emits position.opened/position.updated

### D2 — Add signal trace endpoint

Create an endpoint that returns the full event chain for a specific signal, making it easy to trace what happened to any signal.

```
GET /api/v1/signals/:id/trace
```

**Response:**
```json
{
  "data": {
    "signalId": "abc-123",
    "events": [
      {
        "timestamp": "2025-03-14T10:00:00Z",
        "eventType": "signal.created",
        "payload": { "side": "buy", "symbol": "AAPL", "source": "strategy" }
      },
      {
        "timestamp": "2025-03-14T10:00:01Z",
        "eventType": "risk.evaluation.completed",
        "payload": { "decision": "approved", "checksRun": 12, "checksFailed": 0 }
      },
      {
        "timestamp": "2025-03-14T10:00:02Z",
        "eventType": "paper_trading.order.filled",
        "payload": { "price": "185.25", "qty": 100, "fee": "0.00" }
      },
      {
        "timestamp": "2025-03-14T10:00:02Z",
        "eventType": "portfolio.position.opened",
        "payload": { "positionId": "def-456", "avgEntry": "185.25" }
      }
    ],
    "finalStatus": "order_filled",
    "duration": "2.1s"
  }
}
```

**Implementation:** Query `audit_events` where `payload` contains the signal ID, ordered by timestamp. Include events from all categories (signal, risk, paper_trading, portfolio).

### D3 — Add reconciliation endpoint

Create an endpoint that compares internal records against broker state.

```
GET /api/v1/paper-trading/reconciliation
```

**For Alpaca (equities):**
1. Fetch open positions from Alpaca API: `GET /v2/positions`
2. Fetch open positions from internal database
3. Compare: symbol, qty, side
4. Report mismatches

**For OANDA (forex):**
1. For each mapped pool account: `GET /v3/accounts/{id}/openPositions`
2. Compare against internal forex positions for that account
3. Report mismatches

**Response:**
```json
{
  "data": {
    "timestamp": "2025-03-14T10:00:00Z",
    "alpaca": {
      "status": "matched",
      "internalPositions": 5,
      "brokerPositions": 5,
      "mismatches": []
    },
    "oanda": {
      "status": "mismatch",
      "internalPositions": 3,
      "brokerPositions": 2,
      "mismatches": [
        {
          "symbol": "EUR_USD",
          "poolAccount": 1,
          "internal": { "qty": 10000, "side": "long" },
          "broker": null,
          "issue": "Position exists internally but not at broker"
        }
      ]
    }
  }
}
```

**If broker APIs aren't available:** Return `"status": "unconfigured"` for that broker.

### D4 — Verify event immutability

**Check:**
1. The `audit_events` table has no UPDATE or DELETE triggers
2. The event repository has no `update()` or `delete()` methods
3. The event service only has `create()` / `emit()` methods
4. No endpoint allows event modification

**If any mutation path exists:** Remove it or document the concern.

### D5 — Verify activity feed reads from audit trail

**Check:**
1. The dashboard activity feed queries `audit_events` (not a separate table)
2. The feed displays recent events with correct formatting
3. Category filtering works (signal, risk, paper_trading, portfolio, system)

Query `GET /api/v1/observability/events?limit=20&sortOrder=desc` and verify the response matches what the dashboard feed would display.

---

## Acceptance Criteria

| # | Criterion |
|---|-----------|
| AC1 | Complete event chain documented for successful entry (signal → risk → order → fill → position) |
| AC2 | Complete event chain documented for rejected signal (signal → risk rejection with reason) |
| AC3 | Missing events in the chain are identified and added (or documented as already complete) |
| AC4 | `GET /api/v1/signals/:id/trace` endpoint exists and returns full event chain for a signal |
| AC5 | `GET /api/v1/paper-trading/reconciliation` endpoint exists and compares internal vs broker state |
| AC6 | Reconciliation reports mismatches between internal and broker positions |
| AC7 | Reconciliation handles unconfigured brokers gracefully |
| AC8 | Event immutability verified — no update/delete paths exist for audit events |
| AC9 | Activity feed reads from audit_events table |
| AC10 | All new endpoints require authentication |
| AC11 | No frontend code modified |
| AC12 | Nothing inside /studio modified (except BUILDER_OUTPUT.md) |

## Files to Create

| File | Purpose |
|------|---------|
| `backend/app/signals/router.py` (or existing) | Add `/:id/trace` endpoint |
| `backend/app/paper_trading/reconciliation.py` | Reconciliation logic |
| `backend/app/paper_trading/router.py` (or existing) | Add `/reconciliation` endpoint |

## Files to Modify

| File | What Changes |
|------|-------------|
| Signal router | Add trace endpoint |
| Paper trading router | Add reconciliation endpoint |
| Event emission points (if gaps found) | Add missing event emissions |

## References

- observability_module_spec.md §1 — Event System ("immutable audit trail")
- observability_module_spec.md §2 — Event Catalog (all event types by category)
- paper_trading_module_spec.md §Reconciliation
- cross_cutting_specs.md §2 — Error Handling ("No silent failures in trading logic")
