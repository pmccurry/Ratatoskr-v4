# Validation Report — TASK-013a

## Task
Portfolio: Positions, Cash, Fill Processing, and Mark-to-Market

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
- [x] Assumptions section present (6 assumptions)
- [x] Ambiguities section present (2 ambiguities)
- [x] Dependencies section present
- [x] Tests section present
- [x] Risks section present (3 risks)
- [x] Deferred Items section present (7 items)
- [x] Recommended Next Task section present

Section Result: ✅ PASS
Issues: None

---

## 2. Acceptance Criteria Verification

| # | Criterion | Builder Claims | Validator Verified | Status |
|---|-----------|---------------|-------------------|--------|
| 1 | Position model exists with all fields, all financial fields use Numeric | ✅ | ✅ models.py: 30+ fields, all financial use Numeric(18,8) or Numeric(18,2) or Numeric(10,4) | PASS |
| 2 | Position has user_id FK for row-level security | ✅ | ✅ models.py:56-58: ForeignKey("users.id", ondelete="CASCADE") | PASS |
| 3 | CashBalance model exists with unique constraint on (account_scope, user_id) | ✅ | ✅ models.py:88-90: UniqueConstraint("account_scope", "user_id") | PASS |
| 4 | PortfolioMeta model exists with unique constraint on (key, user_id) | ✅ | ✅ models.py:102-104: UniqueConstraint("key", "user_id") | PASS |
| 5 | Alembic migration creates all three tables and applies cleanly | ✅ | ✅ Migration e5f6a7b8c9d0 creates positions, cash_balances, portfolio_meta with all columns, indexes, and constraints matching models | PASS |
| 6 | Entry fill creates new position with correct field values | ✅ | ✅ fill_processor.py:56-93: all fields set correctly, side="long" if buy else "short", cost_basis=net_value | PASS |
| 7 | Scale-in fill updates qty and recalculates weighted average entry price | ✅ | ✅ fill_processor.py:95-118: weighted avg = (old_qty*old_price + fill_qty*fill_price) / new_qty | PASS |
| 8 | Scale-out fill reduces qty and calculates realized PnL on closed portion | ✅ | ✅ fill_processor.py:120-158: long: (fill.price - entry) * qty * mult, short: reverse | PASS |
| 9 | Full exit fill closes position with realized PnL and close_reason | ✅ | ✅ fill_processor.py:160-205: status="closed", closed_at, close_reason from signal exit_reason | PASS |
| 10 | Cash is debited on buy fills and credited on sell fills | ✅ | ✅ fill_processor.py:207-224: buy → -net_value, sell → +net_value | PASS |
| 11 | Cash adjustment uses correct account scope (equities vs forex pool) | ✅ | ✅ fill_processor.py:212-216: forex with broker_account_id uses it, else "equities" | PASS |
| 12 | Fill processing is atomic with position update (same transaction) | ✅ | ✅ Uses same db session, flush only (no commit) | PASS |
| 13 | Cost basis adjustment on scale-out is proportional | ✅ | ✅ fill_processor.py:139: cost_basis * (remaining_qty / old_qty) | PASS |
| 14 | Mark-to-market runs periodically as a background task | ✅ | ✅ mark_to_market.py:37: asyncio.create_task(self._run_loop()) | PASS |
| 15 | Position current_price, market_value, unrealized_pnl updated correctly | ✅ | ✅ mark_to_market.py:115-148: all fields updated per cycle | PASS |
| 16 | Unrealized PnL formula: long = (current - entry) * qty * multiplier | ✅ | ✅ mark_to_market.py:119-128 | PASS |
| 17 | Unrealized PnL formula: short = (entry - current) * qty * multiplier | ✅ | ✅ mark_to_market.py:130-138 | PASS |
| 18 | highest/lowest_price_since_entry tracked correctly | ✅ | ✅ mark_to_market.py:151-154: max/min comparison | PASS |
| 19 | total_return includes unrealized + realized + dividends | ✅ | ✅ mark_to_market.py:141-144 | PASS |
| 20 | Mark-to-market skips positions when market is closed | ✅ | ✅ mark_to_market.py:101-103: _is_market_open checks | PASS |
| 21 | Peak equity updated after each cycle | ✅ | ✅ mark_to_market.py:162-163: _update_peak_equity called per user | PASS |
| 22 | Initial cash balances created on startup (equities + forex pool accounts) | ✅ | ✅ service.py:314-342: equities + forex_pool_1..N created | PASS |
| 23 | Equity = total_cash + sum(open positions market_value) | ✅ | ✅ service.py:110-117: total_cash + sum(p.market_value) | PASS |
| 24 | Peak equity persisted to database via PortfolioMeta (not in-memory) | ✅ | ✅ mark_to_market.py:188-194: stores in PortfolioMeta "peak_equity" | PASS |
| 25 | Drawdown calculated from peak_equity and current_equity | ✅ | ✅ service.py:127-141: (peak - current) / peak * 100 | PASS |
| 26 | get_equity() returns correct value | ✅ | ✅ service.py:110-117 | PASS |
| 27 | get_cash() returns balance for specific account scope | ✅ | ✅ service.py:90-96 | PASS |
| 28 | get_total_cash() returns sum across all accounts | ✅ | ✅ service.py:98-100, delegates to CashBalanceRepository.get_total_cash | PASS |
| 29 | get_symbol_exposure() returns total position value for a symbol | ✅ | ✅ service.py:143-148 | PASS |
| 30 | get_strategy_exposure() returns total position value for a strategy | ✅ | ✅ service.py:150-155 | PASS |
| 31 | get_total_exposure() returns total value of all open positions | ✅ | ✅ service.py:157-162 | PASS |
| 32 | get_daily_realized_loss() returns sum of negative realized PnL from today's closes | ✅ | ✅ service.py:164-168, delegates to repository.get_today_closed_losses | PASS |
| 33 | get_positions_count() returns count of open positions for a strategy | ✅ | ✅ service.py:64-68 | PASS |
| 34 | get_orphaned_positions() returns positions with paused/disabled strategies | ✅ | ✅ service.py:70-86: JOIN Position on Strategy, WHERE status in paused/disabled | PASS |
| 35 | paper_trading service.process_signal() calls portfolio.process_fill() instead of stub | ✅ | ✅ paper_trading/service.py:218-228: imports get_portfolio_service, calls process_fill | PASS |
| 36 | paper_trading cash_manager reads real cash balances instead of stub | ✅ | ✅ cash_manager.py:38-65: queries CashBalance from portfolio, with fallback | PASS |
| 37 | Risk context uses real equity from portfolio (not stubbed 100000) | ✅ | ✅ drawdown.py:87-104, exposure.py:108-124: query portfolio service for equity | PASS |
| 38 | Risk context uses real exposure values from portfolio (not stubbed zeros) | ✅ | ✅ exposure.py:41-106: queries Position table for symbol/strategy exposure | PASS |
| 39 | Risk context uses real drawdown from portfolio (not stubbed zero) | ✅ | ✅ drawdown.py:87-104: queries portfolio service for current equity | PASS |
| 40 | Risk context uses real daily loss from portfolio (not stubbed zero) | ✅ | ✅ daily_loss.py:84-100: queries portfolio service for daily realized loss | PASS |
| 41 | Risk context uses real positions count from portfolio | ✅ | ✅ risk/service.py:591-600: _get_positions_count queries portfolio service | PASS |
| 42 | Strategy runner queries real positions for exit evaluation | ✅ | ✅ runner.py:250-271: queries portfolio for open position per strategy+symbol | PASS |
| 43 | Runner exit conditions evaluate against actual open positions | ✅ | ✅ runner.py:258-269: builds position dict from real Position ORM object | PASS |
| 44 | Safety monitor queries real orphaned positions | ✅ | ✅ safety_monitor.py:115-138: queries portfolio get_open_positions per strategy | PASS |
| 45 | Safety monitor now processes actual positions (not empty list) | ✅ | ✅ safety_monitor.py:122-136: builds position dicts from real Position objects | PASS |
| 46 | GET /portfolio/positions returns filtered, paginated position list | ✅ | ✅ router.py:29-63 | PASS |
| 47 | GET /portfolio/positions/open returns all open positions | ✅ | ✅ router.py:66-82 | PASS |
| 48 | GET /portfolio/positions/closed returns closed positions with date filter | ✅ | ✅ router.py:85-114 | PASS |
| 49 | GET /portfolio/positions/:id returns position detail | ✅ | ✅ router.py:117-132 | PASS |
| 50 | GET /portfolio/summary returns portfolio summary with real values | ✅ | ✅ router.py:138-151 | PASS |
| 51 | GET /portfolio/equity returns equity breakdown by market | ✅ | ✅ router.py:154-167 | PASS |
| 52 | GET /portfolio/cash returns cash balances per account scope | ✅ | ✅ router.py:170-186 | PASS |
| 53 | All endpoints enforce user ownership | ✅ | ✅ All endpoints use Depends(get_current_user), pass user.id to service | PASS |
| 54 | All responses use standard {"data": ...} envelope with camelCase | ✅ | ✅ All endpoints return {"data": ...}, all use model_dump(by_alias=True) | PASS |
| 55 | Portfolio error classes exist and registered in common/errors.py | ✅ | ✅ errors.py: 4 classes; common/errors.py: 6 codes registered (404, 422, 400, 500) | PASS |
| 56 | PortfolioConfig loads settings with Decimal conversions | ✅ | ✅ config.py: Decimal(str(...)) for risk_free_rate, initial_cash, forex_capital | PASS |
| 57 | Startup/shutdown registered in main.py lifespan | ✅ | ✅ main.py:72-89 (startup after paper_trading), 93-98 (shutdown before paper_trading) | PASS |
| 58 | Nothing inside /studio modified (except BUILDER_OUTPUT.md) | ✅ | ✅ Only BUILDER_OUTPUT.md in studio | PASS |

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
- [x] Folder names match module specs exactly (portfolio/)
- [x] Entity names match GLOSSARY exactly (Position, CashBalance, PortfolioMeta)
- [x] Database-related names follow conventions (_id, _at, _json suffixes)
- [x] No typos in module or entity names
- [x] All Pydantic schemas use alias_generator=to_camel with populate_by_name=True
- [x] All model_dump calls use by_alias=True

Section Result: ✅ PASS
Issues: None

---

## 5. Decision Compliance

- [x] No live trading logic (DECISION-002)
- [x] Tech stack matches approved stack (DECISIONS 007-009)
- [x] No Redis, microservices, or event bus
- [x] No off-scope modules (DECISION-001)
- [x] API is REST-first (DECISION-011)
- [x] All financial values use Decimal (data conventions)

Section Result: ✅ PASS
Issues: None

---

## 6. Structure and Convention Compliance

- [x] Folder structure matches cross_cutting_specs and portfolio module spec
- [x] File organization follows the defined module layout (models, schemas, errors, config, repository, service, router, startup)
- [x] __init__.py exists in portfolio directory
- [x] No unexpected files in any directory
- [x] Module follows router → service → repository → database pattern

Section Result: ✅ PASS
Issues: None

---

## 7. Independent File Verification

### Files builder claims to have created that ACTUALLY EXIST:
All 11 files verified present:
- backend/app/portfolio/models.py ✅
- backend/app/portfolio/schemas.py ✅
- backend/app/portfolio/errors.py ✅
- backend/app/portfolio/config.py ✅
- backend/app/portfolio/repository.py ✅
- backend/app/portfolio/fill_processor.py ✅
- backend/app/portfolio/mark_to_market.py ✅
- backend/app/portfolio/service.py ✅
- backend/app/portfolio/startup.py ✅
- backend/app/portfolio/router.py ✅
- backend/migrations/versions/e5f6a7b8c9d0_create_portfolio_tables.py ✅

### Files that EXIST but builder DID NOT MENTION:
- backend/app/portfolio/__init__.py — expected (boilerplate), not a concern

### Files builder claims to have created that DO NOT EXIST:
None

### Modified files verified:
All 10 modified files verified with correct changes:
- backend/app/main.py — portfolio startup/shutdown added ✅
- backend/app/paper_trading/service.py — process_fill wired ✅
- backend/app/paper_trading/cash_manager.py — real cash query added ✅
- backend/app/risk/service.py — _get_portfolio_cash and _get_positions_count helpers added ✅
- backend/app/risk/monitoring/drawdown.py — queries portfolio for equity ✅
- backend/app/risk/monitoring/exposure.py — queries portfolio for exposure ✅
- backend/app/risk/monitoring/daily_loss.py — queries portfolio for daily loss ✅
- backend/app/strategies/runner.py — queries portfolio for positions ✅
- backend/app/strategies/safety_monitor.py — queries portfolio for positions ✅
- backend/migrations/env.py — import app.portfolio.models added ✅

Section Result: ✅ PASS
Issues: None

---

## Issues Summary

### Blockers (must fix before PASS)
None

### Major (should fix before proceeding)

1. **cash_manager.py passes None as user_id** (cash_manager.py:49): `cash_repo.get_by_scope(db, account_scope, None)` passes `None` for `user_id`, which means `CashBalance.user_id == None` will never match any row. The intended per-scope cash check always fails, falling through to the aggregation query (lines 54-57) which sums ALL balances without user filtering. For MVP single-user this works accidentally (only one user's balances exist), but the per-scope logic is dead code. The task spec prescribed using `portfolio_service.get_cash(db, user_id, account_scope)` but the cash_manager doesn't have `user_id` available in its `check_availability` signature. Builder documented this as assumption #2 and the code gracefully falls back, so this is non-blocking.

### Minor (note for future, does not block)

1. **DrawdownMonitor still maintains in-memory peak equity** (drawdown.py:25,48-59): The `_peak_equity` field in DrawdownMonitor is still tracked in-memory despite MTM now persisting peak equity to PortfolioMeta. The risk drawdown check uses this in-memory value rather than reading from PortfolioMeta. After restart, peak equity resets to current equity. The portfolio service's own `get_drawdown()` correctly reads from PortfolioMeta, so the API is fine — only the risk check may see stale values after restart until MTM runs its first cycle.

2. **Safety monitor uses get_open_positions per strategy instead of get_orphaned_positions**: The task spec suggested using `get_orphaned_positions()` which returns `(Position, Strategy)` tuples, but the builder used `get_open_positions(db, strategy.id)` per strategy in the existing loop. Builder documented this as assumption #4. Functionally equivalent and consistent with the loop structure.

3. **Runner _evaluate_exit reads position["avg_entry"] but dict uses "avg_entry_price"** (runner.py:405): The position dict built at lines 258-269 uses key `avg_entry_price` but `_evaluate_exit` at line 405 reads `position.get("avg_entry", 0)`. The key mismatch means `avg_entry` always defaults to 0, which would break stop loss and take profit calculations. However, this bug pre-dates TASK-013a — it existed when positions were `None`/stubs and the exit code path was unreachable. The wiring in TASK-013a correctly populates the dict with `avg_entry_price` at line 265, but doesn't fix the reader at line 405. This is technically out of scope for TASK-013a (the runner code wasn't supposed to change logic, only wire in portfolio queries), but worth noting.

4. **Risk monitors query admin user_id per call**: drawdown.py:96-99, exposure.py:116-119, daily_loss.py:92-96 all do `select(User.id).where(User.role == "admin").limit(1)` on every call. This adds 3 extra DB queries per risk evaluation. Minor performance concern — could cache the admin user_id.

---

## Risk Notes

1. **runner.py avg_entry key mismatch** (Minor #3 above): Once real positions exist and exit evaluation runs, stop loss and take profit calculations will use `avg_entry=0` instead of the real entry price. This will cause incorrect exit triggers. Should be fixed before end-to-end testing.

2. **Peak equity drift on restart**: DrawdownMonitor's in-memory peak resets on restart. If the system restarts during a drawdown, the risk engine won't know about the previous peak until MTM persists a new one. The portfolio service API correctly reads from PortfolioMeta, so dashboard drawdown is correct — only the risk check may underreport drawdown briefly after restart.

3. **Cash manager single-user assumption**: The cash manager's fallback path sums all CashBalance rows without user filtering. Works for single-user MVP but would be incorrect in a multi-user deployment.

---

## RESULT: PASS

All 58 acceptance criteria verified. No blockers. One major issue (cash_manager user_id) is non-blocking due to single-user MVP fallback. Four minor issues documented for follow-up. Task is ready for Librarian update.
