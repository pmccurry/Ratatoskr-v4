# TASK-036 — Live Connectivity Verification & Post-Hardening Bug Fixes

## Goal

Verify real broker connectivity with Alpaca and OANDA keys that are now in `.env`, run the readiness check, and fix all bugs identified by Validators across TASK-032 through TASK-035. After this task, the platform connects to real brokers and all known issues are resolved.

## Depends On

TASK-035

## Scope

**In scope:**
- Verify Alpaca WebSocket connects with real keys (start backend, check logs)
- Verify OANDA stream connects with real keys (check logs)
- Run `scripts/readiness_check.py` and fix any failures
- Fix all 11 bugs listed below from Validator reports
- Document live connectivity results

**Out of scope:**
- New features
- Frontend changes (except if readiness check surfaces frontend issues)
- Test creation

---

## Bug Fixes

### BF-1 — Health endpoint `subscribedSymbols` key mismatch (TASK-032 Major #1)

**File:** `backend/app/main.py:219`
**Problem:** `h.get("subscribed_symbols", 0)` but `ConnectionHealth.to_dict()` returns `"subscribedSymbols"` (camelCase). Subscribed symbol count always shows 0.
**Fix:** Change to `h.get("subscribedSymbols", 0)`

### BF-2 — WebSocket `receive()` None triggers unnecessary reconnection (TASK-032 Minor #1)

**File:** `backend/app/market_data/streams/alpaca_ws.py`
**Problem:** Returning `None` for non-bar message batches causes the manager to treat it as "connection lost" and trigger a full reconnect cycle.
**Fix:** Add an internal `while True` loop inside `receive()` that skips non-bar messages and only returns when it has bar data or a real disconnection occurs:

```python
async def receive(self):
    while True:
        try:
            raw = await self._ws.recv()
            messages = json.loads(raw)
            bars = [m for m in messages if m.get("T") == "b"]
            if bars:
                return self._parse_bars(bars)
            # No bars in this batch — keep waiting, don't return None
            continue
        except (ConnectionClosed, ConnectionClosedError):
            return None  # Real disconnection
```

### BF-3 — Pool `seed_accounts()` orphans records on virtual→real transition (TASK-033 Minor #1)

**File:** `backend/app/paper_trading/forex_pool/pool_manager.py`
**Problem:** Looks up existing accounts by `account_id_str` (the new ID). When switching from virtual (`forex_pool_1`) to real (`101-001-XXXXX-001`), the old record is orphaned.
**Fix:** Look up by slot number instead of account ID. Add a `slot_number` field or use a deterministic lookup pattern:

```python
# Instead of: existing = await repo.get_by_account_id(account_id_str)
# Use: existing = await repo.get_by_slot(i)
# Or: use a composite key like f"pool_slot_{i}" stored in a metadata field
```

If adding a field is too invasive, use a simpler approach: delete all pool accounts on seed and recreate them. Since seeding only runs on startup, this is safe:

```python
async def seed_accounts(self, db):
    # Clear existing pool accounts
    await self._repo.delete_pool_accounts(db)
    # Create fresh from config
    for i in range(1, self.pool_size + 1):
        ...
```

### BF-4 — OANDA adapter inline `import asyncio` (TASK-033 Minor #2)

**File:** `backend/app/market_data/adapters/oanda.py:72` (approximate)
**Problem:** `import asyncio` inside function body instead of module top level.
**Fix:** Move `import asyncio` to module top-level imports (same fix as Alpaca adapter in TASK-032).

### BF-5 — Shadow exit fee asymmetry (TASK-033 Minor #4)

**File:** `backend/app/paper_trading/shadow/tracker.py`
**Problem:** Exit fee uses manual calculation (`fee_spread_bps / 10000 * price * qty`) while entry uses the full `FillSimulationEngine`. Shadow PnL may differ from real PnL by ~15 bps on exit.
**Fix:** Use the `FillSimulationEngine` for shadow exit fills too:

```python
# Instead of manual fee calculation:
exit_fill = await self._fill_engine.simulate(exit_order, reference_price)
```

If the fill engine isn't available in the shadow tracker context, extract the fee calculation into a shared utility and use it in both places.

### BF-6 — Unused `require_admin` import in reconciliation (TASK-034 Minor #1)

**File:** `backend/app/paper_trading/router.py:381`
**Problem:** `require_admin` imported but not used. Reconciliation uses `get_current_user`.
**Fix:** Either remove the unused import, or change the reconciliation endpoint to use `require_admin` (reconciliation should arguably be admin-only). Recommend making it admin-only:

```python
@router.get("/reconciliation", dependencies=[Depends(require_admin)])
```

### BF-7 — OANDA reconciliation missing qty/side comparison (TASK-034 Minor #3)

**File:** `backend/app/paper_trading/reconciliation.py`
**Problem:** Alpaca reconciliation checks qty and side mismatches, but OANDA only checks presence/absence.
**Fix:** Add qty/side comparison for OANDA matches (same pattern as Alpaca):

```python
# When both internal and broker have the same symbol+account:
if abs(internal_qty - broker_qty) > Decimal("0.001") or internal_side != broker_side:
    mismatches.append({
        "symbol": symbol,
        "poolAccount": account_num,
        "internal": {"qty": str(internal_qty), "side": internal_side},
        "broker": {"qty": str(broker_qty), "side": broker_side},
        "issue": "Quantity or side mismatch"
    })
```

### BF-8 — Reconciliation uses `float()` for qty comparison (TASK-034 Minor #4)

**File:** `backend/app/paper_trading/reconciliation.py:71,77`
**Problem:** Converts Decimal qty to float for Alpaca comparison. Per project convention, financial values should use Decimal.
**Fix:** Keep qty as Decimal throughout. Parse Alpaca response qty as Decimal:

```python
broker_qty = Decimal(str(alpaca_position["qty"]))
internal_qty = position.qty  # already Decimal
if abs(internal_qty - broker_qty) > Decimal("0.001"):
    ...
```

### BF-9 — Rate limit variables missing from `.env.example` (TASK-035 Minor #1)

**File:** `.env.example`
**Problem:** Task spec defined `AUTH_LOGIN_RATE_LIMIT` and `AUTH_LOGIN_RATE_WINDOW_SEC` env vars but they weren't added. Rate limits are hardcoded.
**Fix:** Add the variables to `.env.example` and make the rate limiter read from config:

Add to `.env.example`:
```env
# === Rate Limiting ===
AUTH_LOGIN_RATE_LIMIT=5
AUTH_LOGIN_RATE_WINDOW_SEC=60
AUTH_REFRESH_RATE_LIMIT=10
AUTH_REFRESH_RATE_WINDOW_SEC=60
AUTH_PASSWORD_CHANGE_RATE_LIMIT=3
AUTH_PASSWORD_CHANGE_RATE_WINDOW_SEC=60
```

Add to Settings class and update `rate_limiter.py` to read from config instead of hardcoding.

### BF-10 — `check_sensitive_logs` is a no-op (TASK-035 Minor #3)

**File:** `scripts/readiness_check.py:174-177`
**Problem:** Function immediately returns `"pass"` without scanning anything.
**Fix:** Implement a basic grep through Python log files:

```python
def check_sensitive_logs():
    """Scan log format strings for sensitive patterns."""
    sensitive_patterns = ["password", "secret", "token", "api_key", "api_secret"]
    import glob
    issues = []
    for py_file in glob.glob("backend/app/**/*.py", recursive=True):
        with open(py_file) as f:
            for line_num, line in enumerate(f, 1):
                if "logger." in line or "logging." in line:
                    for pattern in sensitive_patterns:
                        if pattern in line.lower() and "%" in line or "f'" in line or 'f"' in line:
                            issues.append(f"{py_file}:{line_num}")
    if issues:
        return f"Potential sensitive data in logs: {', '.join(issues[:3])}"
    return "pass"
```

### BF-11 — `check_kill_switch` always returns "warn" (TASK-035 Minor #4)

**File:** `scripts/readiness_check.py:148-155`
**Problem:** Can't check kill switch state without authentication, always returns "warn".
**Fix:** Use the same login approach as `check_admin_password` to get a token, then check kill switch:

```python
def check_kill_switch():
    """Check kill switch is deactivated."""
    # Login to get token
    login_resp = requests.post(f"{API_URL}/auth/login", json={
        "email": os.environ.get("ADMIN_SEED_EMAIL", "admin@ratatoskr.local"),
        "password": os.environ.get("READINESS_CHECK_PASSWORD", "")
    })
    if login_resp.status_code != 200:
        return "warn"  # Can't authenticate to check
    
    token = login_resp.json().get("data", {}).get("accessToken", "")
    resp = requests.get(f"{API_URL}/risk/kill-switch/status",
                       headers={"Authorization": f"Bearer {token}"})
    if resp.status_code == 200:
        data = resp.json().get("data", {})
        if data.get("isActive", False):
            return "Kill switch is ACTIVE — deactivate before going live"
        return "pass"
    return "warn"
```

---

## Live Connectivity Verification

### V1 — Start backend with real keys

1. Ensure `.env` has `ALPACA_API_KEY`, `ALPACA_API_SECRET`, `OANDA_ACCESS_TOKEN`, `OANDA_ACCOUNT_ID`
2. Start backend: `cd backend && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000`
3. Watch startup logs for:
   - `Alpaca WebSocket connected and authenticated`
   - `OANDA pricing stream connected`
   - `Universe filter: N symbols`
   - All background tasks starting
4. Document what succeeds and what fails

### V2 — Verify data pipeline

1. Check health: `curl http://localhost:8000/api/v1/health`
2. Check watchlist: `curl -H "Authorization: Bearer <token>" http://localhost:8000/api/v1/market-data/watchlist`
3. If during market hours: check bars are streaming
4. If outside market hours: document that bars aren't expected
5. Check backfill status

### V3 — Run readiness check

1. Run: `uv run python scripts/readiness_check.py`
2. Document all check results
3. Fix any failures that are fixable (e.g., if migrations aren't current, run them)
4. Document warnings that require operator action (e.g., "change admin password")

---

## Acceptance Criteria

| # | Criterion |
|---|-----------|
| AC1 | Health endpoint `subscribedSymbols` shows correct count (not always 0) |
| AC2 | WebSocket `receive()` doesn't trigger unnecessary reconnection on non-bar messages |
| AC3 | Pool `seed_accounts()` doesn't orphan records when switching virtual↔real |
| AC4 | OANDA adapter has `import asyncio` at module top level |
| AC5 | Shadow exit fees use the same calculation as entry (no asymmetry) |
| AC6 | Reconciliation endpoint is admin-only (or unused import removed) |
| AC7 | OANDA reconciliation checks qty/side mismatches (not just presence/absence) |
| AC8 | Reconciliation uses `Decimal` for qty comparison (not float) |
| AC9 | Rate limit variables in `.env.example` and configurable via Settings |
| AC10 | `check_sensitive_logs` in readiness script performs actual scanning |
| AC11 | `check_kill_switch` authenticates and checks real state (or falls back to warn gracefully) |
| AC12 | Backend starts with real Alpaca keys without crashing (result documented) |
| AC13 | Backend starts with real OANDA keys without crashing (result documented) |
| AC14 | `readiness_check.py` runs and all results documented |
| AC15 | No frontend code modified |
| AC16 | Nothing inside /studio modified (except BUILDER_OUTPUT.md) |

---

## Files to Modify

| File | What Changes |
|------|-------------|
| `backend/app/main.py` | BF-1: Fix `subscribedSymbols` key |
| `backend/app/market_data/streams/alpaca_ws.py` | BF-2: Internal loop in `receive()` |
| `backend/app/paper_trading/forex_pool/pool_manager.py` | BF-3: Slot-based lookup or clear-and-recreate |
| `backend/app/market_data/adapters/oanda.py` | BF-4: Move `import asyncio` to top |
| `backend/app/paper_trading/shadow/tracker.py` | BF-5: Use fill engine for exit fees |
| `backend/app/paper_trading/router.py` | BF-6: Make reconciliation admin-only |
| `backend/app/paper_trading/reconciliation.py` | BF-7 + BF-8: OANDA qty/side check, Decimal comparison |
| `backend/app/common/rate_limiter.py` | BF-9: Read from config instead of hardcoding |
| `backend/app/common/config.py` | BF-9: Add rate limit settings |
| `.env.example` | BF-9: Add rate limit variables |
| `scripts/readiness_check.py` | BF-10 + BF-11: Real log scanning, authenticated kill switch check |

## Files NOT to Touch

- Frontend code
- Studio files (except BUILDER_OUTPUT.md)
- Docker/startup scripts
- Test files

---

## Builder Notes

- **Real API keys are in `.env`.** Start the backend and observe what happens. Document everything — successes, failures, errors, warnings.
- **Market hours matter for Alpaca.** If outside US market hours (9:30 AM - 4:00 PM ET), WebSocket will connect but no bars will stream. That's normal.
- **Forex runs 24/5.** OANDA data should stream outside US market hours (Sunday 5 PM ET through Friday 5 PM ET).
- **BF-3 (pool orphan) has two approaches.** The simpler "clear and recreate on startup" approach is recommended unless allocations need to survive restarts. If they do, implement slot-based lookup.
- **BF-5 (shadow fees) might require refactoring.** If the fill engine isn't accessible from the shadow tracker, extract the fee calculation into a shared utility. Don't duplicate the math.
- **Document live results thoroughly.** The BUILDER_OUTPUT.md should include exact log lines, health endpoint responses, and readiness check output. This is the first time real broker connections are verified.

## References

- TASK-032 VALIDATION.md — Major #1 (health key), Minor #1 (reconnection)
- TASK-033 VALIDATION.md — Minor #1 (pool orphan), Minor #2 (inline import), Minor #4 (shadow fees)
- TASK-034 VALIDATION.md — Minor #1 (unused import), Minor #3 (OANDA reconciliation), Minor #4 (float qty)
- TASK-035 VALIDATION.md — Minor #1 (rate limit vars), Minor #3 (sensitive logs no-op), Minor #4 (kill switch warn)
