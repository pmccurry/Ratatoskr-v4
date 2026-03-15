# Builder Output — TASK-021

## Task
Backend Bug Fixes

## Completion Checklist
- [x] All deliverables created
- [x] All acceptance criteria addressed
- [x] No off-scope files created
- [x] No off-scope files modified
- [x] No locked decisions violated
- [x] Output follows naming conventions
- [x] Output follows folder structure conventions

## Files Created
None

## Files Modified
- backend/app/portfolio/options_lifecycle.py — FIX-B1: Capture position.qty into `qty_at_expiry` before zeroing, use that for RealizedPnlEntry.qty_closed
- backend/app/signals/service.py — FIX-B2: Added valid transitions `risk_approved -> order_filled/order_rejected` and `risk_modified -> order_filled/order_rejected`
- backend/app/paper_trading/service.py — FIX-B2: Replaced direct signal status writes with calls to SignalService.update_signal_status() via get_signal_service()
- backend/app/risk/monitoring/drawdown.py — FIX-B3: Removed in-memory `_peak_equity` fallback, all reads go through PortfolioMeta via portfolio service, returns "degraded" status when portfolio service unavailable
- backend/app/portfolio/snapshots.py — FIX-B4: Added `_last_daily_run` tracking and `_check_daily_jobs()` method to periodic loop, triggers DailyPortfolioJobs.run_daily() after market close on new trading days
- backend/app/paper_trading/cash_manager.py — FIX-B6: Added `_estimate_fee()` method and included estimated fee in `calculate_required_cash()` for buy orders
- backend/app/portfolio/metrics.py — FIX-B7: Added clarifying comment explaining Sortino ratio denominator convention (N = total periods, not just negative returns)
- backend/app/risk/checks/base.py — FIX-B8: Added `proposed_position_value: Decimal` field to RiskContext dataclass
- backend/app/risk/checks/exposure.py — FIX-B8: Updated SymbolExposureCheck, StrategyExposureCheck, and PortfolioExposureCheck to use `context.proposed_position_value` instead of estimating from position size limit percentage
- backend/app/risk/service.py — FIX-B8: Populated `proposed_position_value` in `_build_context()` using signal qty, current price, and contract multiplier

## Files Deleted
None

## Acceptance Criteria Status
1. FIX-B1: Options expiration PnL entry has correct qty_closed (not zero) — ✅ Done (qty captured into `qty_at_expiry` before zeroing)
2. FIX-B2: Paper trading updates signal status through SignalService (not direct write) — ✅ Done (uses `get_signal_service().update_signal_status()`)
3. FIX-B2: Signal module accepts transitions: risk_approved/risk_modified -> order_filled/order_rejected — ✅ Done (added to `_VALID_TRANSITIONS`)
4. FIX-B3: DrawdownMonitor reads peak equity from portfolio service only (no in-memory fallback) — ✅ Done (removed `_peak_equity` instance variable, reads from PortfolioMetaRepository)
5. FIX-B3: DrawdownMonitor returns "degraded" status if portfolio service unavailable — ✅ Done (returns `threshold_status: "degraded"` when portfolio service unavailable)
6. FIX-B4: DailyPortfolioJobs runs automatically after market close on new trading days — ✅ Done (`_check_daily_jobs()` triggers after 21:00 UTC)
7. FIX-B4: Trading day detection integrated into snapshot periodic loop — ✅ Done (called in `_run_loop()` after snapshots)
8. FIX-B6: Cash manager includes estimated fee in required cash for buy orders — ✅ Done (`_estimate_fee()` added, uses config fee values per market)
9. FIX-B7: Sortino ratio has clarifying comment about denominator convention — ✅ Done
10. FIX-B8: Exposure checks use actual proposed position value (not estimated from limit) — ✅ Done (all 3 checks use `context.proposed_position_value`)
11. FIX-B8: RiskContext includes proposed_position_value field — ✅ Done
12. No new features or modules created — ✅ Done
13. No frontend code modified — ✅ Done
14. Nothing inside /studio modified (except BUILDER_OUTPUT.md) — ✅ Done

## Assumptions Made
1. **Market close hour**: Used 21:00 UTC as the market close detection threshold for daily jobs. This is approximately 4:00 PM ET (EST). During EDT, market close is 20:00 UTC, so daily jobs may run an hour late during summer. This is acceptable since daily jobs are not time-critical to the minute.
2. **Fee estimation for cash reservation**: Used the same fee config values (fee_per_trade_equities, fee_spread_bps_forex, fee_per_trade_options) from PaperTradingConfig. Forex fees are estimated as a percentage of gross value (spread in bps), while equities and options use flat per-trade fees.
3. **Proposed position value calculation**: When signal doesn't have `requested_qty` (signals don't carry qty — that's determined by paper trading), the value is estimated from the strategy's position sizing config. This covers the common sizing methods (fixed_qty, fixed_dollar, percent_equity).
4. **DrawdownMonitor.reset_peak_equity**: Delegates to `portfolio_service.reset_peak_equity(db, user_id, admin_user)` which matches the existing service signature.

## Ambiguities Encountered
None — task and specs were unambiguous. Each bug had clear root cause and fix description.

## Dependencies Discovered
None — all required modules, services, and singletons already exist.

## Tests Created
None — not required by this task.

## Risks or Concerns
1. **DrawdownMonitor "degraded" status**: Callers of `get_current_drawdown()` (e.g., risk service, router) should handle the "degraded" threshold_status appropriately. The risk service's auto-kill-switch logic checks for "catastrophic" status — it will not trigger on "degraded", which is the correct behavior.
2. **Daily jobs timing**: The `_MARKET_CLOSE_HOUR_UTC = 21` constant is hardcoded. If the platform needs to support markets in other timezones, this should be made configurable.

## Deferred Items
None — all deliverables complete.

## Recommended Next Task
Continue with Milestone 13 — Testing and Validation. Create task packets for backend unit tests covering the critical paths fixed here (risk evaluation pipeline, paper trading fill flow, portfolio daily jobs, drawdown monitoring).
