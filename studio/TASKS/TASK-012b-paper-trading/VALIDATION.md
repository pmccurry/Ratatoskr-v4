# Validation Report — TASK-012b

## Task
Paper Trading: Forex Pool, Alpaca Paper API, and Shadow Tracking

## Pre-Flight Checks
- [x] Task packet read completely
- [x] Builder output read completely
- [x] All referenced specs read
- [x] DECISIONS.md read
- [x] GLOSSARY.md read
- [x] cross_cutting_specs.md read
- [x] Repo files independently inspected (not just builder summary)

---

## 1. Builder Output Quality

### Is BUILDER_OUTPUT.md complete?
- [x] Completion Checklist present and filled
- [x] Files Created section present and non-empty
- [x] Files Modified section present
- [x] Files Deleted section present
- [x] Acceptance Criteria Status — every criterion listed and marked
- [x] Assumptions section present (5 assumptions documented)
- [x] Ambiguities section present (2 ambiguities documented)
- [x] Dependencies section present
- [x] Tests section present
- [x] Risks section present (3 risks documented)
- [x] Deferred Items section present
- [x] Recommended Next Task section present

Section Result: ✅ PASS
Issues: None

---

## 2. Acceptance Criteria Verification

| # | Criterion | Builder Claims | Validator Verified | Status |
|---|-----------|---------------|-------------------|--------|
| 1 | BrokerAccount model exists with all fields, unique account_id | ✅ | ✅ models.py has BrokerAccount with broker, account_id (unique=True), account_type, label, is_active, capital_allocation (Numeric), credentials_env_key, timestamps | PASS |
| 2 | AccountAllocation model exists with all fields and three indexes | ✅ | ✅ models.py has AccountAllocation with account_id FK, strategy_id FK, symbol, side, status, allocated_at, released_at. Three indexes on (account_id,symbol,status), (strategy_id,status), (symbol,status) | PASS |
| 3 | All financial fields use Numeric | ✅ | ✅ capital_allocation uses Numeric(18,2). Shadow models use Numeric for all price/value/fee/qty fields | PASS |
| 4 | Alembic migration creates tables and applies cleanly | ✅ | ✅ Migration f6a7b8c9d0e1 creates broker_accounts, account_allocations, shadow_positions, shadow_fills with all columns, FKs, and indexes matching models | PASS |
| 5 | find_available_account correctly queries for unoccupied accounts per pair | ✅ | ✅ allocation.py get_available_for_symbol uses NOT IN subquery filtering by symbol and status='active' | PASS |
| 6 | Account with EUR_USD occupied but GBP_USD free IS available for GBP_USD | ✅ | ✅ Query filters occupied subquery by symbol, so different pairs on same account are independent | PASS |
| 7 | Account with EUR_USD occupied is NOT available for another EUR_USD | ✅ | ✅ Subquery excludes accounts with active allocation for the same symbol | PASS |
| 8 | allocate() creates an active allocation record | ✅ | ✅ pool_manager.py allocate() creates AccountAllocation with status="active" via repo | PASS |
| 9 | release() sets status=released and released_at on the allocation | ✅ | ✅ allocation.py release() sets status="released" and released_at=utcnow | PASS |
| 10 | seed_accounts() creates virtual accounts from config on startup | ✅ | ✅ pool_manager.py seed_accounts() creates pool_size accounts with labels "Forex Pool {i}" and account_type="paper_virtual" | PASS |
| 11 | Pool status returns per-account allocations and per-pair capacity | ✅ | ✅ pool_manager.py get_pool_status() returns accounts with allocations, pair_capacity dict, total_accounts, fully_empty | PASS |
| 12 | Forex orders route through ForexPoolExecutor | ✅ | ✅ service.py _get_executor returns forex_pool_executor when market=="forex" | PASS |
| 13 | ForexPoolExecutor allocates an account before filling | ✅ | ✅ forex_pool.py submit_order finds available account, allocates, then simulates fill | PASS |
| 14 | ForexPoolExecutor rejects with "no_available_account" when pool is full | ✅ | ✅ Returns OrderResult(success=False, rejection_reason="no_available_account") when no account available | PASS |
| 15 | Account released when forex exit fill is processed | ✅ | ✅ service.py lines 258-269 release forex pool allocation after portfolio processing for exit/scale_out fills | PASS |
| 16 | broker_account_id set on PaperOrder and PaperFill for forex orders | ✅ | ✅ forex_pool.py submit_order sets order.broker_account_id to account.account_id | PASS |
| 17 | AlpacaPaperExecutor submits orders to Alpaca paper API | ✅ | ✅ alpaca_paper.py submit_order POSTs to {base_url}/v2/orders | PASS |
| 18 | Alpaca auth headers sent correctly | ✅ | ✅ Headers include APCA-API-KEY-ID and APCA-API-SECRET-KEY from settings | PASS |
| 19 | broker_order_id stored on PaperOrder from Alpaca response | ✅ | ✅ Extracts response["id"] and sets order.broker_order_id | PASS |
| 20 | Fill data extracted from Alpaca order status | ✅ | ✅ _poll_alpaca_fill polls GET /v2/orders/{id}, extracts filled_qty, filled_avg_price, filled_at | PASS |
| 21 | Fallback to SimulatedExecutor if Alpaca API unavailable | ✅ | ✅ _fallback_submit and _fallback_fill delegate to self._simulated with settings check | PASS |
| 22 | Fallback logs a warning with reason | ✅ | ✅ logger.warning with reason string in both fallback methods | PASS |
| 23 | Equities route through AlpacaPaperExecutor when config mode = "paper" | ✅ | ✅ service.py _get_executor returns alpaca_executor for equities when mode="paper"; startup creates AlpacaPaperExecutor when execution_mode_equities=="paper" | PASS |
| 24 | Equities route through SimulatedExecutor when config mode = "simulation" | ✅ | ✅ _get_executor falls through to self._simulated_executor when not mode="paper" | PASS |
| 25 | ShadowFill model exists with all fields, all Numeric | ✅ | ✅ models.py ShadowFill has all spec fields, all price/qty/value/fee fields are Numeric | PASS |
| 26 | ShadowPosition model exists with all fields including SL/TP/trailing | ✅ | ✅ models.py ShadowPosition has stop_loss_price, take_profit_price, trailing_stop_price, highest_price_since_entry — all Numeric nullable | PASS |
| 27 | Migration creates both shadow tables | ✅ | ✅ Migration creates shadow_positions and shadow_fills with all columns and indexes | PASS |
| 28 | Shadow tracking only activates for "no_available_account" rejections | ✅ | ✅ tracker.py should_track checks rejection_reason == "no_available_account" | PASS |
| 29 | Shadow tracking does NOT activate for risk rejections or other reasons | ✅ | ✅ should_track returns False for any rejection_reason != "no_available_account" | PASS |
| 30 | Shadow tracking is configurable (SHADOW_TRACKING_ENABLED, FOREX_ONLY) | ✅ | ✅ should_track checks settings.shadow_tracking_enabled and settings.shadow_tracking_forex_only | PASS |
| 31 | Shadow entry fill uses same slippage/fee models as real fills | ✅ | ✅ tracker.py uses self._fill_engine (same FillSimulationEngine instance) | PASS |
| 32 | Shadow position created with SL/TP/trailing from strategy config | ✅ | ✅ create_shadow_entry reads exit_rules from strategy config_json for SL/TP/trailing values | PASS |
| 33 | Shadow position exit conditions evaluated by ShadowEvaluator | ✅ | ✅ evaluator.py evaluate_shadow_positions checks SL, TP, trailing stop for each open shadow position | PASS |
| 34 | Shadow position closes with realized PnL on exit | ✅ | ✅ tracker.py close_shadow_position calculates realized_pnl with long/short formulas, sets status="closed" | PASS |
| 35 | Shadow positions are marked to market | ✅ | ✅ evaluator.py mark_to_market_shadows updates current_price and unrealized_pnl on all open shadow positions | PASS |
| 36 | Shadow fills never affect real positions | ✅ | ✅ Shadow fills stored in separate shadow_fills table, no interaction with PaperFill or Position tables | PASS |
| 37 | Shadow positions never affect real portfolio equity | ✅ | ✅ Shadow positions in separate shadow_positions table, no portfolio service calls | PASS |
| 38 | Shadow PnL never included in real performance metrics | ✅ | ✅ Shadow PnL computed independently in ShadowPositionRepository.get_comparison_stats, separate from portfolio metrics | PASS |
| 39 | Shadow positions never trigger real risk checks | ✅ | ✅ Shadow positions never create signals — they bypass the signal→risk→order pipeline entirely | PASS |
| 40 | Shadow positions never consume account pool allocations | ✅ | ✅ Shadow tracking happens after pool rejection, no allocation created for shadow positions | PASS |
| 41 | Strategy runner evaluates shadow position exits (step 7b) | ✅ | ✅ runner.py lines 309-325 imports ShadowEvaluator, calls evaluate_shadow_positions after real position processing | PASS |
| 42 | GET /paper-trading/forex-pool/status returns pool dashboard data | ✅ | ✅ router.py endpoint returns PoolStatusResponse with accounts, pair_capacity, total_accounts, fully_empty | PASS |
| 43 | GET /paper-trading/forex-pool/accounts returns account list | ✅ | ✅ router.py endpoint returns list of BrokerAccountResponse | PASS |
| 44 | GET /paper-trading/shadow/positions returns shadow positions | ✅ | ✅ router.py endpoint with strategy_id, status filters and pagination | PASS |
| 45 | GET /paper-trading/shadow/positions/:id returns detail with fills | ✅ | ✅ router.py endpoint returns position + fills in data envelope | PASS |
| 46 | GET /paper-trading/shadow/comparison returns real vs shadow performance | ✅ | ✅ router.py endpoint returns list of ShadowComparisonResponse per strategy | PASS |
| 47 | All new endpoints use {"data": ...} envelope with camelCase | ✅ | ✅ All endpoints wrap responses in {"data": ...} and use model_dump(by_alias=True) with to_camel alias_generator | PASS |
| 48 | Startup seeds forex accounts and initializes new executors | ✅ | ✅ startup.py seeds accounts, creates ForexPoolExecutor, AlpacaPaperExecutor, ShadowTracker | PASS |
| 49 | Nothing inside /studio modified (except BUILDER_OUTPUT.md) | ✅ | ✅ Only BUILDER_OUTPUT.md added in studio/TASKS/TASK-012b-paper-trading/ | PASS |

Section Result: ✅ PASS
Issues: None

---

## 3. Scope Check

- [x] No files created outside task deliverables
- [x] No files modified outside task scope
- [x] No modules added that aren't in the approved list
- [x] No architectural changes or new patterns introduced
- [x] No live trading logic present
- [x] No dependencies added beyond what the task requires

Section Result: ✅ PASS
Issues: None

---

## 4. Naming Compliance

- [x] Python files use snake_case
- [x] Folder names match module specs exactly (forex_pool, shadow, executors)
- [x] Entity names match GLOSSARY exactly (BrokerAccount, AccountAllocation, ShadowPosition, ShadowFill)
- [x] Database-related names follow conventions (_id, _at suffixes)
- [x] No typos in module or entity names

Section Result: ✅ PASS
Issues: None

---

## 5. Decision Compliance

- [x] No live trading logic (DECISION-002)
- [x] Tech stack matches approved stack (DECISIONS 007-009)
- [x] No Redis, microservices, or event bus
- [x] No off-scope modules (DECISION-001)
- [x] API is REST-first (DECISION-011)
- [x] Forex account pool model matches DECISION-016 (per-pair allocation, FIFO netting)
- [x] Shadow tracking matches DECISION-017 (only for "no_available_account", forex only, isolated)
- [x] Broker paper trading for equities, internal simulation for forex matches DECISION-018

Section Result: ✅ PASS
Issues: None

---

## 6. Structure and Convention Compliance

- [x] Folder structure matches cross_cutting_specs and paper_trading module spec
- [x] File organization follows the defined module layout (models, schemas, service, router, startup, executors/, forex_pool/, shadow/)
- [x] __init__.py files exist in forex_pool/, shadow/, executors/ packages
- [x] No unexpected files in any directory

Section Result: ✅ PASS
Issues: None

---

## 7. Independent File Verification

### Files builder claims to have created that ACTUALLY EXIST:
- [x] backend/app/paper_trading/forex_pool/__init__.py
- [x] backend/app/paper_trading/forex_pool/pool_manager.py
- [x] backend/app/paper_trading/forex_pool/allocation.py
- [x] backend/app/paper_trading/shadow/__init__.py
- [x] backend/app/paper_trading/shadow/tracker.py
- [x] backend/app/paper_trading/shadow/evaluator.py
- [x] backend/app/paper_trading/shadow/repository.py
- [x] backend/app/paper_trading/executors/forex_pool.py
- [x] backend/app/paper_trading/executors/alpaca_paper.py
- [x] backend/migrations/versions/f6a7b8c9d0e1_create_forex_pool_shadow_tables.py

All 10 files verified present.

### Files that EXIST but builder DID NOT MENTION:
None found. All files in the modified directories are either pre-existing (from TASK-012a) or listed by the builder.

### Files builder claims to have created that DO NOT EXIST:
None — all 10 files exist.

Section Result: ✅ PASS
Issues: None

---

## Issues Summary

### Blockers (must fix before PASS)
None

### Major (should fix before proceeding)
None

### Minor (note for future, does not block)

1. **Unused variable in allocation.py**: `occupied_subq` variable at line 25 is defined but unused — the actual NOT IN subquery is written inline at lines 37-43. Dead code should be removed.

2. **Shadow exit fill reuses entry signal_id**: In tracker.py close_shadow_position (around line 168), the exit ShadowFill's `signal_id` is set to `position.entry_signal_id` rather than the actual exit signal's ID. For shadow positions this is functionally acceptable since shadow exits are triggered by price conditions (not real signals), but the field is semantically misleading.

3. **Shadow/forex-pool endpoints lack user ownership enforcement**: The shadow positions and forex pool endpoints accept auth (get_current_user) but don't filter results by user_id. Shadow positions don't have a user_id column, so all users see all shadow positions. In a single-user MVP this is fine, but should be addressed before multi-user support.

4. **Runner accesses service._shadow_tracker (private attribute)**: runner.py step 7b accesses `service._shadow_tracker` directly rather than through a public interface. This is noted in BUILDER_OUTPUT.md assumption #3. A public accessor method would be cleaner.

5. **ForexPoolExecutor.submit_order signature differs from Executor ABC**: submit_order adds an optional `db` parameter not in the base class. The service uses isinstance check to pass db only to ForexPoolExecutor. This is noted in BUILDER_OUTPUT.md as both an assumption and an ambiguity, and is handled correctly in practice.

---

## Risk Notes

1. **Alpaca fill polling uses synchronous sleep**: The fill polling loop in alpaca_paper.py uses `await asyncio.sleep(1)` up to 3 times. In a high-throughput scenario this could block the event loop for the calling coroutine. The builder notes this and suggests WebSocket-based fills as a future enhancement.

2. **Shadow position accumulation**: Shadow positions are never cleaned up. Over time this could grow the shadow_positions and shadow_fills tables unboundedly. The builder has noted this in Deferred Items.

3. **Comparison endpoint performance**: The shadow/comparison endpoint (router.py lines 267-365) runs multiple queries per strategy in a loop. For many strategies this could be slow. Consider batch queries in the future.

---

## RESULT: PASS

All 49 acceptance criteria independently verified. No blocker or major issues found. 5 minor issues documented for future cleanup. Task is ready for Librarian update.
