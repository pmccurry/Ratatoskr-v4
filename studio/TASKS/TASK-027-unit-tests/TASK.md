# TASK-027 — Unit Tests: Trading Pipeline (Risk, Fills, PnL, Signals, Forex Pool)

## Goal

Write unit tests for the trading pipeline's core logic: risk checks, fill simulation, PnL calculations, signal deduplication/expiry, and forex account pool allocation. These are pure-logic tests with no database dependency.

## Depends On

TASK-026 (test infrastructure and conftest)

## Scope

**In scope:**
- `tests/unit/test_risk_checks.py`
- `tests/unit/test_fill_simulation.py`
- `tests/unit/test_pnl_calculation.py`
- `tests/unit/test_signal_dedup.py`
- `tests/unit/test_forex_pool_allocation.py`

**Out of scope:**
- Integration tests (TASK-028)
- Tests requiring a database
- Application code changes

---

## Deliverables

### D1 — `tests/unit/test_risk_checks.py`

Test each of the 12 risk checks independently and the ordering/pipeline behavior.

**Individual check tests:**

| Check | Test cases |
|-------|-----------|
| 1. Kill switch | Active → reject entry; active → allow exit; inactive → pass |
| 2. Strategy enable | Disabled strategy → reject; enabled → pass; paused → reject |
| 3. Symbol tradability | Untradable symbol → reject; tradable → pass |
| 4. Market hours | Outside hours → reject entry; outside hours → allow exit; inside hours → pass |
| 5. Duplicate order | Same symbol+side pending → reject; no pending → pass |
| 6. Position limit | At max positions → reject new; under limit → pass |
| 7. Position sizing | Zero qty → reject; negative → reject; valid → pass; exceeds max → modify |
| 8. Symbol exposure | Would exceed limit → reject; within limit → pass |
| 9. Strategy exposure | Would exceed limit → reject; within limit → pass |
| 10. Portfolio exposure | Would exceed limit → reject; within limit → pass |
| 11. Drawdown | Exceeds max → reject; within limit → pass; catastrophic → activate kill switch |
| 12. Daily loss | Exceeds limit → reject; within limit → pass |

**Pipeline behavior tests:**

```python
class TestRiskPipeline:
    def test_checks_run_in_order(self):
        """Kill switch checked before exposure limits"""

    def test_first_rejection_stops_pipeline(self):
        """If check 3 rejects, checks 4-12 are not evaluated"""

    def test_exit_signals_skip_entry_checks(self):
        """Exit signals skip: position limit, sizing, exposure, drawdown, daily loss"""

    def test_all_pass_returns_approved(self):
        """All checks pass → signal status = risk_approved"""

    def test_rejection_includes_reason(self):
        """Rejected signal has check name and human-readable reason"""

    def test_modification_returns_modified(self):
        """Position sizing modified → signal status = risk_modified with new qty"""
```

**Mock setup:** Each test mocks the dependencies (portfolio service, position repo, risk config) to isolate the check logic. Use `unittest.mock.MagicMock` or `pytest-mock`.

### D2 — `tests/unit/test_fill_simulation.py`

Test the internal fill simulation engine (slippage, fees, net value calculation).

**Slippage tests:**

```python
class TestSlippage:
    def test_buy_slippage_increases_price(self):
        """Buy at $100 with 5bps slippage → $100.05"""

    def test_sell_slippage_decreases_price(self):
        """Sell at $100 with 5bps slippage → $99.95"""

    def test_zero_slippage(self):
        """0bps → execution price = reference price"""

    def test_slippage_amount_calculation(self):
        """slippage_amount = |execution_price - reference_price| * qty"""

    def test_slippage_per_market(self):
        """Equities: 5bps, Forex: 2bps, Options: 10bps (per config)"""
```

**Fee tests:**

```python
class TestFees:
    def test_flat_fee_per_trade(self):
        """Equities: flat $0.00 per trade (commission-free)"""

    def test_spread_bps_fee_forex(self):
        """Forex: 15bps spread → fee = gross_value * 15 / 10000"""

    def test_per_share_fee(self):
        """If per_share: fee = qty * fee_per_share"""

    def test_percent_fee(self):
        """If percent: fee = gross_value * percent / 100"""

    def test_zero_fee(self):
        """$0 fee → net_value = gross_value"""
```

**Net value tests:**

```python
class TestNetValue:
    def test_buy_net_value(self):
        """Buy: net_value = gross_value + fee (you pay more)"""

    def test_sell_net_value(self):
        """Sell: net_value = gross_value - fee (you receive less)"""

    def test_full_fill_calculation(self):
        """Buy 100 shares at $50, 5bps slippage, $1 fee:
           execution_price = 50.025
           gross_value = 5002.50
           net_value = 5003.50"""
```

**Options fill tests:**

```python
class TestOptionsFill:
    def test_options_contract_multiplier(self):
        """Options qty=1 at $3.00 → gross_value = 1 * 3.00 * 100 = 300"""

    def test_options_slippage(self):
        """10bps slippage on options premium"""
```

### D3 — `tests/unit/test_pnl_calculation.py`

Test all four fill-to-position scenarios and PnL math.

**New position (new_open):**

```python
class TestNewPosition:
    def test_long_new_open(self):
        """Buy 100 AAPL at $150 → qty=100, avg_entry=150, unrealized=0"""

    def test_short_new_open(self):
        """Sell 100 AAPL at $150 → qty=-100, avg_entry=150, unrealized=0"""

    def test_options_new_open(self):
        """Buy 5 AAPL calls at $3.00 → qty=5, avg_entry=3.00, multiplier=100"""
```

**Scale-in (add to existing):**

```python
class TestScaleIn:
    def test_long_scale_in_weighted_average(self):
        """Position: 100 @ $150. Buy 50 more @ $160.
           New avg_entry = (100*150 + 50*160) / 150 = $153.33
           New qty = 150"""

    def test_multiple_scale_ins(self):
        """Three successive scale-ins → correct running weighted avg"""

    def test_scale_in_preserves_realized_pnl(self):
        """Scale-in does not affect previously realized PnL"""
```

**Scale-out (partial close):**

```python
class TestScaleOut:
    def test_long_partial_close_profit(self):
        """Position: 100 @ $150. Sell 50 @ $170.
           gross_pnl = (170 - 150) * 50 = $1000
           net_pnl = gross_pnl - fee
           Remaining: 50 @ $150 (avg_entry unchanged)"""

    def test_long_partial_close_loss(self):
        """Sell 50 @ $140.
           gross_pnl = (140 - 150) * 50 = -$500"""

    def test_short_partial_close_profit(self):
        """Short 100 @ $150. Buy 50 @ $140.
           gross_pnl = (150 - 140) * 50 = $500"""

    def test_short_partial_close_loss(self):
        """Buy 50 @ $160.
           gross_pnl = (150 - 160) * 50 = -$500"""

    def test_partial_close_does_not_change_avg_entry(self):
        """avg_entry_price stays the same after partial close"""

    def test_realized_pnl_accumulates(self):
        """Two partial closes → realized_pnl = sum of both"""
```

**Full close:**

```python
class TestFullClose:
    def test_long_full_close_profit(self):
        """Position: 100 @ $150. Sell 100 @ $170.
           realized_pnl = (170-150)*100 - fee = $1,994 (with $6 total fee example)
           Position qty = 0, status = closed"""

    def test_long_full_close_loss(self):
        """Sell 100 @ $130. realized_pnl = -$2,006"""

    def test_full_close_after_scale_ins(self):
        """Multiple scale-ins then full close → PnL uses weighted avg entry"""

    def test_full_close_zeros_qty(self):
        """After full close: position.qty = 0"""
```

**Unrealized PnL (mark-to-market):**

```python
class TestUnrealizedPnl:
    def test_long_unrealized_profit(self):
        """Long 100 @ $150, current price $170.
           unrealized_pnl = (170-150)*100 = $2000"""

    def test_long_unrealized_loss(self):
        """Long 100 @ $150, current price $130.
           unrealized_pnl = (130-150)*100 = -$2000"""

    def test_short_unrealized_profit(self):
        """Short 100 @ $150, current price $130.
           unrealized_pnl = (150-130)*100 = $2000"""

    def test_unrealized_pnl_percent(self):
        """unrealized_pnl_percent = (current - entry) / entry * 100"""

    def test_options_multiplier_in_unrealized(self):
        """Options: unrealized includes contract multiplier"""
```

**All PnL tests must use `Decimal` and verify exact values, not approximate floats.**

### D4 — `tests/unit/test_signal_dedup.py`

Test signal deduplication and expiration logic.

**Deduplication tests:**

```python
class TestSignalDedup:
    def test_duplicate_within_window(self):
        """Same strategy, same symbol, same side, within dedup window → rejected"""

    def test_duplicate_outside_window(self):
        """Same signal but outside dedup window → allowed"""

    def test_different_symbol_not_dedup(self):
        """Same strategy, different symbol → not duplicate"""

    def test_different_side_not_dedup(self):
        """Same symbol, buy vs sell → not duplicate"""

    def test_different_strategy_not_dedup(self):
        """Different strategy, same symbol+side → not duplicate"""

    def test_exit_signals_exempt(self):
        """Exit signals are never deduplicated"""

    def test_manual_signals_exempt(self):
        """source='manual' signals are never deduplicated"""

    def test_safety_signals_exempt(self):
        """source='safety_monitor' signals are never deduplicated"""

    def test_system_signals_exempt(self):
        """source='system' signals are never deduplicated"""

    def test_zero_window_disables_dedup(self):
        """dedup_window_bars=0 → no dedup, every signal passes"""

    def test_scale_in_subject_to_dedup(self):
        """signal_type='scale_in' with source='strategy' → subject to dedup"""
```

**Expiration tests:**

```python
class TestSignalExpiry:
    def test_signal_expires_after_ttl(self):
        """Signal older than expires_at → status becomes 'expired'"""

    def test_signal_not_expired_within_ttl(self):
        """Signal within TTL → not expired"""

    def test_processed_signal_not_expired(self):
        """Signal already in 'risk_approved' → not expired even if past TTL"""

    def test_expires_at_computed_from_timeframe(self):
        """1h strategy → expires_at = created_at + 5min (SIGNAL_EXPIRY_SECONDS)"""
```

### D5 — `tests/unit/test_forex_pool_allocation.py`

Test forex account pool allocation and release logic.

```python
class TestForexPoolAllocation:
    def test_allocate_available_account(self):
        """4 accounts, none allocated for EURUSD → allocate first available"""

    def test_reject_when_all_accounts_busy(self):
        """4 accounts, all have active EURUSD allocations → reject signal"""

    def test_same_account_different_pair(self):
        """Account allocated for EURUSD can also take GBPUSD"""

    def test_release_on_position_close(self):
        """Close position → release allocation → account available again"""

    def test_allocation_tracks_strategy(self):
        """Allocation records which strategy allocated the account"""

    def test_first_come_priority(self):
        """first_come: allocates to the first unallocated account found"""

    def test_concurrent_allocation_safety(self):
        """Two simultaneous requests for same pair → only one succeeds
        (mock the check to simulate race condition)"""

    def test_pool_size_respected(self):
        """Pool of 4 accounts → can have at most 4 concurrent same-pair positions"""
```

---

## Acceptance Criteria

| # | Criterion |
|---|-----------|
| AC1 | All 12 risk checks have at least 2 test cases each (pass and reject) |
| AC2 | Risk pipeline tests verify ordering, early termination, and exit signal exemptions |
| AC3 | Slippage tests cover buy (price up) and sell (price down) with correct math |
| AC4 | Fee tests cover at least 3 fee models (flat, spread_bps, percent or per_share) |
| AC5 | Net value tests verify buy (gross + fee) and sell (gross - fee) |
| AC6 | All 4 fill-to-position types tested: new_open, scale_in, scale_out, full_close |
| AC7 | Scale-in weighted average entry price calculation verified with exact Decimal values |
| AC8 | Realized PnL verified for long profit, long loss, short profit, short loss |
| AC9 | Unrealized PnL verified for long and short positions |
| AC10 | Signal dedup tests cover: within window, outside window, exempt sources (exit, manual, safety, system) |
| AC11 | Signal expiry tests cover: expired, not expired, already-processed not expired |
| AC12 | Forex pool tests cover: allocation, rejection when full, release, different pairs on same account |
| AC13 | All financial calculations use `Decimal` (not float) |
| AC14 | All tests are pure unit tests — no database, no network, mocked dependencies |
| AC15 | `pytest tests/unit/ -v` runs without import errors |
| AC16 | No application code modified |
| AC17 | Nothing inside /studio modified (except BUILDER_OUTPUT.md) |

## Files to Create

| File | Purpose |
|------|---------|
| `backend/tests/unit/test_risk_checks.py` | Risk check unit tests |
| `backend/tests/unit/test_fill_simulation.py` | Fill simulation unit tests |
| `backend/tests/unit/test_pnl_calculation.py` | PnL calculation unit tests |
| `backend/tests/unit/test_signal_dedup.py` | Signal dedup/expiry unit tests |
| `backend/tests/unit/test_forex_pool_allocation.py` | Forex pool allocation unit tests |

## Files NOT to Touch

Everything outside `backend/tests/`.

## References

- cross_cutting_specs.md §6 — Testing Strategy (file names, coverage expectations)
- risk_engine_module_spec.md §3 — Risk Check Sequence (ordering, exit exemptions)
- risk_engine_module_spec.md §4 — Risk Checks Detailed (all 12 checks)
- paper_trading_module_spec.md §Fill Simulation (slippage, fees, net value)
- portfolio_module_spec.md §Fill Processing (4 fill types, weighted avg, PnL formulas)
- signals_module_spec.md §Deduplication (window, exemptions)
- signals_module_spec.md §Expiration (TTL, status transitions)
- paper_trading_module_spec.md §Forex Account Pool (allocation, release, contention)
