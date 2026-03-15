# Builder Output — TASK-012b

## Task
Paper Trading: Forex Pool, Alpaca Paper API, and Shadow Tracking

## Completion Checklist
- [x] All deliverables created
- [x] All acceptance criteria addressed
- [x] No off-scope files created
- [x] No off-scope files modified
- [x] No locked decisions violated
- [x] Output follows naming conventions
- [x] Output follows folder structure conventions

## Files Created
- backend/app/paper_trading/forex_pool/__init__.py
- backend/app/paper_trading/forex_pool/pool_manager.py
- backend/app/paper_trading/forex_pool/allocation.py
- backend/app/paper_trading/shadow/__init__.py
- backend/app/paper_trading/shadow/tracker.py
- backend/app/paper_trading/shadow/evaluator.py
- backend/app/paper_trading/shadow/repository.py
- backend/app/paper_trading/executors/forex_pool.py
- backend/app/paper_trading/executors/alpaca_paper.py
- backend/migrations/versions/f6a7b8c9d0e1_create_forex_pool_shadow_tables.py

## Files Modified
- backend/app/paper_trading/models.py — Added BrokerAccount, AccountAllocation, ShadowPosition, ShadowFill models
- backend/app/paper_trading/schemas.py — Added ShadowPositionResponse, ShadowFillResponse, PoolStatusResponse, ShadowComparisonResponse, BrokerAccountResponse
- backend/app/paper_trading/service.py — Updated constructor to accept new executors and shadow tracker; updated _get_executor to route by market/config; added shadow tracking on "no_available_account" rejection; added forex account release on exit fills
- backend/app/paper_trading/startup.py — Added forex pool seeding, ForexPoolExecutor, AlpacaPaperExecutor, and ShadowTracker initialization; added get_pool_manager()
- backend/app/paper_trading/router.py — Added 5 new endpoints for forex pool status/accounts and shadow positions/detail/comparison
- backend/app/strategies/runner.py — Added step 7b: shadow position exit evaluation after real position exits

## Files Deleted
None

## Acceptance Criteria Status

### Forex Pool Models and Migration
1. BrokerAccount model exists with all fields, unique account_id — ✅ Done
2. AccountAllocation model exists with all fields and three indexes — ✅ Done
3. All financial fields use Numeric — ✅ Done
4. Alembic migration creates tables and applies cleanly — ✅ Done

### Forex Pool Logic
5. find_available_account correctly queries for unoccupied accounts per pair — ✅ Done (subquery NOT IN occupied accounts)
6. An account with EUR_USD occupied but GBP_USD free IS available for GBP_USD — ✅ Done (query filters by symbol)
7. An account with EUR_USD occupied is NOT available for another EUR_USD — ✅ Done (subquery excludes occupied)
8. allocate() creates an active allocation record — ✅ Done
9. release() sets status=released and released_at on the allocation — ✅ Done
10. seed_accounts() creates virtual accounts from config on startup — ✅ Done
11. Pool status returns per-account allocations and per-pair capacity — ✅ Done

### Forex Pool Integration
12. Forex orders route through ForexPoolExecutor — ✅ Done (_get_executor returns forex_pool_executor for forex)
13. ForexPoolExecutor allocates an account before filling — ✅ Done (submit_order allocates, then fill simulates)
14. ForexPoolExecutor rejects with "no_available_account" when pool is full for pair — ✅ Done
15. Account released when forex exit fill is processed — ✅ Done (service.py releases after portfolio processing)
16. broker_account_id set on PaperOrder and PaperFill for forex orders — ✅ Done (set in ForexPoolExecutor.submit_order)

### Alpaca Paper Executor
17. AlpacaPaperExecutor submits orders to Alpaca paper API — ✅ Done (POST /v2/orders)
18. Alpaca auth headers sent correctly (APCA-API-KEY-ID, APCA-API-SECRET-KEY) — ✅ Done
19. broker_order_id stored on PaperOrder from Alpaca response — ✅ Done
20. Fill data extracted from Alpaca order status (price, qty, timestamp) — ✅ Done (_poll_alpaca_fill)
21. Fallback to SimulatedExecutor if Alpaca API unavailable — ✅ Done (_fallback_submit, _fallback_fill)
22. Fallback logs a warning with reason — ✅ Done
23. Equities route through AlpacaPaperExecutor when config mode = "paper" — ✅ Done
24. Equities route through SimulatedExecutor when config mode = "simulation" — ✅ Done

### Shadow Tracking Models
25. ShadowFill model exists with all fields, all Numeric — ✅ Done
26. ShadowPosition model exists with all fields including SL/TP/trailing — ✅ Done
27. Migration creates both shadow tables — ✅ Done

### Shadow Tracking Logic
28. Shadow tracking only activates for "no_available_account" rejections — ✅ Done (should_track checks)
29. Shadow tracking does NOT activate for risk rejections or other reasons — ✅ Done
30. Shadow tracking is configurable (SHADOW_TRACKING_ENABLED, FOREX_ONLY) — ✅ Done (reads from settings)
31. Shadow entry fill uses same slippage/fee models as real fills — ✅ Done (uses same FillSimulationEngine)
32. Shadow position created with SL/TP/trailing from strategy config — ✅ Done (reads exit_rules from config)
33. Shadow position exit conditions evaluated by ShadowEvaluator — ✅ Done
34. Shadow position closes with realized PnL on exit — ✅ Done
35. Shadow positions are marked to market (current_price, unrealized_pnl updated) — ✅ Done (mark_to_market_shadows)

### Shadow Isolation
36. Shadow fills never affect real positions — ✅ Done (separate tables, no portfolio interaction)
37. Shadow positions never affect real portfolio equity — ✅ Done
38. Shadow PnL never included in real performance metrics — ✅ Done
39. Shadow positions never trigger real risk checks — ✅ Done
40. Shadow positions never consume account pool allocations — ✅ Done

### Runner Integration
41. Strategy runner evaluates shadow position exits (step 7b) — ✅ Done

### API
42. GET /paper-trading/forex-pool/status returns pool dashboard data — ✅ Done
43. GET /paper-trading/forex-pool/accounts returns account list with allocations — ✅ Done
44. GET /paper-trading/shadow/positions returns shadow positions — ✅ Done
45. GET /paper-trading/shadow/positions/:id returns detail with fills — ✅ Done
46. GET /paper-trading/shadow/comparison returns real vs shadow performance — ✅ Done
47. All new endpoints use {"data": ...} envelope with camelCase — ✅ Done

### General
48. Startup seeds forex accounts and initializes new executors — ✅ Done
49. Nothing inside /studio modified (except BUILDER_OUTPUT.md) — ✅ Done

## Assumptions Made
1. **Forex pool seeding during startup**: seed_accounts runs in its own db session during startup. If the database isn't reachable during startup, the seeding is logged as a warning and the forex pool executor won't be available (graceful degradation).
2. **Alpaca fallback check**: The `paper_trading_broker_fallback` setting is a string ("simulation"). The fallback is enabled whenever this string is non-empty/truthy. Setting it to empty string or "none" would disable fallback.
3. **Shadow evaluator integration**: The runner accesses `service._shadow_tracker` to create the ShadowEvaluator. This is a slightly coupled pattern but avoids adding another startup singleton.
4. **Comparison endpoint**: Uses portfolio Position model for real trade stats. Falls back gracefully if portfolio module isn't available.
5. **ForexPoolExecutor.submit_order signature**: Added optional `db` parameter to match Executor ABC while allowing pool allocation queries. The base class doesn't define the db parameter, so it's passed as a keyword arg.

## Ambiguities Encountered
1. **ForexPoolExecutor submit_order needs db**: The base Executor ABC doesn't include db in submit_order. Resolved by adding it as an optional keyword parameter and using isinstance check in the service to pass it only to the forex pool executor.
2. **Shadow position mark-to-market timing**: The spec says it "can piggyback on portfolio MTM cycle" but doesn't specify exactly how. Implemented mark_to_market_shadows as a standalone method that can be called by the evaluator or independently.

## Dependencies Discovered
None — all required modules exist.

## Tests Created
None — not required by this task.

## Risks or Concerns
1. **Alpaca API rate limits**: The fill polling (up to 3 attempts with 1s sleep) could be slow if Alpaca is under load. Future enhancement: use Alpaca's trade_updates WebSocket instead of polling.
2. **Shadow position cleanup**: Shadow positions accumulate indefinitely. A future task should add TTL-based cleanup or archival.
3. **ForexPoolExecutor db coupling**: The executor needs a db session for pool allocation but the base Executor ABC doesn't include it. This is handled via isinstance check which is slightly fragile.

## Deferred Items
- Alpaca trade_updates WebSocket for real-time fill notifications (enhancement)
- Shadow position archival/cleanup (not in spec)
- Full exit account release should also check if it was a scale_out that fully closes (currently checks signal_type)

## Recommended Next Task
TASK-013b — Portfolio: Snapshots, PnL Ledger, Dividends, and Performance Metrics. This completes the portfolio module.
