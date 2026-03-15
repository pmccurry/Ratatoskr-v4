# Validation Report — TASK-040

## Task
Backtest Engine (Backend)

## Pre-Flight Checks
- [x] Task packet read completely
- [x] Builder output read completely
- [x] All referenced specs read (strategy_module_spec, paper_trading_module_spec, cross_cutting_specs)
- [x] DECISIONS.md read
- [x] GLOSSARY.md read
- [x] cross_cutting_specs.md read
- [x] Repo files independently inspected (not just builder summary)

---

## 1. Builder Output Quality

### Is BUILDER_OUTPUT.md complete?
- [x] Completion Checklist present and filled
- [x] Files Created section present — 10 files listed
- [x] Files Modified section present — 1 file (main.py)
- [x] Files Deleted section present (None)
- [x] Acceptance Criteria Status — all 22 criteria listed and marked
- [x] Assumptions section present with 7 documented assumptions
- [x] Ambiguities section present with 2 items
- [x] Dependencies section present (None — correct)
- [x] Tests section present (None — not required by task)
- [x] Risks section present with 3 documented concerns
- [x] Deferred Items section present (None)
- [x] Recommended Next Task section present (TASK-041)

Section Result: ✅ PASS
Issues: None

---

## 2. Acceptance Criteria Verification

| # | Criterion | Builder Claims | Validator Verified | Status |
|---|-----------|---------------|-------------------|--------|
| AC1 | Migration creates backtest_runs, backtest_trades, backtest_equity_curve | ✅ | ✅ Migration i9d0e1f2a3b4 creates all 3 tables with correct columns, FKs (CASCADE), indexes including composite (backtest_id, bar_index) | PASS |
| AC2 | POST /strategies/{id}/backtest runs sync, returns results | ✅ | ✅ trigger_backtest endpoint creates run, awaits BacktestRunner.run(), returns BacktestRunResponse | PASS |
| AC3 | Runner walks bars chronologically, evaluates conditions | ✅ | ✅ Per-symbol loop with bar-by-bar iteration, calls existing ConditionEngine.evaluate() on sliding window | PASS |
| AC4 | Indicator warmup: extra bars before start_date, no signals during warmup | ✅ | ✅ _load_bars() fetches warmup bars before start_date; warmup_complete flag gates entry signals | PASS |
| AC5 | Fill simulation applies slippage and fees | ✅ | ✅ _simulate_fill() adds 0.5 pips slippage (Decimal), _calculate_fees() applies 2 bps spread | PASS |
| AC6 | Stop loss exit: closes when bar low/high crosses SL | ✅ | ✅ _check_exits() handles SL for long (bar.low <= sl_price) and short (bar.high >= sl_price) with pip values | PASS |
| AC7 | Take profit exit: closes when bar high/low crosses TP | ✅ | ✅ _check_exits() handles TP for long (bar.high >= tp_price) and short (bar.low <= tp_price) | PASS |
| AC8 | Signal-based exit: opposite signal closes position | ✅ | ✅ _process_entry() checks signal_exit flag, closes opposite direction positions before opening new | PASS |
| AC9 | Time-based exit: closes after max_hold_bars | ✅ | ✅ _check_exits() checks (bar_index - entry_bar_index) >= max_hold_bars | PASS |
| AC10 | Open positions force-closed at end with reason="end_of_data" | ✅ | ✅ After bar loop, remaining open positions closed with reason="end_of_data" | PASS |
| AC11 | All 4 position sizing types work | ✅ | ✅ sizing.py implements fixed, fixed_cash, percent_equity, percent_risk with Decimal math and JPY pip handling | PASS |
| AC12 | Performance metrics computed correctly | ✅ | ✅ metrics.py computes 27 metrics: trade counts, PnL, ratios, risk (Sharpe, drawdown), duration, streaks, excursion, capital. Edge cases handled (no trades, zero std, no losers) | PASS |
| AC13 | Equity curve recorded at appropriate intervals | ✅ | ✅ record_equity() samples every 10 bars for 1m, every bar for 1h/4h/1d, plus on trade events | PASS |
| AC14 | GET /backtests/{id} returns run with metrics | ✅ | ✅ get_backtest endpoint returns BacktestRunResponse with metrics field | PASS |
| AC15 | GET /backtests/{id}/trades paginated | ✅ | ✅ get_backtest_trades with page/pageSize params, default 50 per page | PASS |
| AC16 | GET /backtests/{id}/equity-curve with downsampling | ✅ | ✅ get_equity_curve with sample param (ge=10, le=5000), preserves last point | PASS |
| AC17 | GET /strategies/{id}/backtests list per strategy | ✅ | ✅ list_backtests endpoint, paginated, ordered by created_at desc | PASS |
| AC18 | Strategy config frozen at backtest time | ✅ | ✅ config_version.config_json copied to backtest_run.strategy_config at creation | PASS |
| AC19 | Failed backtests store error, status="failed" | ✅ | ✅ try/except catches exceptions, sets status="failed" and error=str(exc) | PASS |
| AC20 | All financial calculations use Decimal | ✅ | ✅ State, sizing, runner all use Decimal; metrics converts to float only for final JSON output | PASS |
| AC21 | No frontend code modified | ✅ | ✅ git diff shows no frontend/ changes | PASS |
| AC22 | Nothing inside /studio modified (except BUILDER_OUTPUT.md) | ✅ | ✅ git diff shows no studio/ changes | PASS |

Section Result: ✅ PASS
Issues: None

---

## 3. Scope Check

- [x] No files created outside task deliverables — all in backend/app/backtesting/ and migrations/versions/
- [x] No files modified outside task scope — only backend/app/main.py (+3 lines for router registration)
- [x] No modules added outside approved list — backtesting is new module approved by this task
- [x] No architectural changes — imports and reuses existing ConditionEngine, indicator registry, FormulaParser
- [x] No live trading logic present — simulation only
- [x] No dependencies added beyond task requirements — uses only existing stdlib + project modules

Section Result: ✅ PASS
Issues: None

---

## 4. Naming Compliance

- [x] Python files use snake_case: sizing.py, metrics.py, runner.py, state.py, etc.
- [x] Folder name matches convention: backend/app/backtesting/
- [x] Entity names match GLOSSARY pattern: BacktestRun, BacktestTrade, BacktestEquityPoint
- [x] Database columns follow conventions: strategy_id, entry_time, exit_price, pnl_percent, drawdown_pct (_id, _at, _pct suffixes)
- [x] Table names: backtest_runs, backtest_trades, backtest_equity_curve (snake_case, plural)
- [x] API schemas use camelCase aliases via alias_generator=to_camel
- [x] No typos in module or entity names

Section Result: ✅ PASS
Issues: None

---

## 5. Decision Compliance

- [x] No live trading logic (DECISION-002) — simulation only
- [x] Tech stack matches: Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.x, Alembic (DECISIONS 007-009)
- [x] No Redis, microservices, or event bus — synchronous in-process engine
- [x] No off-scope modules (DECISION-001)
- [x] All financial values use Decimal (not float) — verified throughout
- [x] API is REST-first (DECISION-011) — standard REST endpoints with pagination

Section Result: ✅ PASS
Issues: None

---

## 6. Structure and Convention Compliance

- [x] Module follows standard layout: models.py, router.py, repository.py, schemas.py + domain-specific (runner, state, sizing, metrics)
- [x] __init__.py exists in backtesting module
- [x] Migration properly versioned and chains from previous (h8c9d0e1f2a3)
- [x] Migration has correct upgrade() and downgrade() (drops in reverse dependency order)
- [x] No unexpected files in any directory — exactly 9 Python files + __init__.py

Section Result: ✅ PASS
Issues: None

---

## 7. Independent File Verification

### Files builder claims to have created that ACTUALLY EXIST:
All 10 files verified:
1. `backend/app/backtesting/__init__.py` ✅ (empty init)
2. `backend/app/backtesting/models.py` ✅ (3 SQLAlchemy models)
3. `backend/app/backtesting/state.py` ✅ (BacktestState, BacktestTradeRecord, EquityPoint)
4. `backend/app/backtesting/sizing.py` ✅ (4 sizing types + JPY handling)
5. `backend/app/backtesting/metrics.py` ✅ (27 metrics + Sharpe + streaks)
6. `backend/app/backtesting/runner.py` ✅ (BacktestRunner with full bar replay)
7. `backend/app/backtesting/repository.py` ✅ (CRUD + downsampling)
8. `backend/app/backtesting/schemas.py` ✅ (Request/Response with camelCase)
9. `backend/app/backtesting/router.py` ✅ (2 routers, 5 endpoints)
10. `backend/migrations/versions/i9d0e1f2a3b4_create_backtest_tables.py` ✅ (3 tables)

### Files builder claims to have modified that ACTUALLY CHANGED:
- `backend/app/main.py` — ✅ +3 lines: import and 2 router registrations

### Files that EXIST but builder DID NOT MENTION:
None found.

### Files builder claims that DO NOT EXIST:
None — all files verified.

Section Result: ✅ PASS
Issues: None

---

## Implementation Quality Notes

### Reuse of Existing Code
- ConditionEngine imported from `app.strategies.conditions.engine` — no reimplementation ✅
- Indicator registry imported from `app.strategies.indicators` — no reimplementation ✅
- FormulaParser imported from `app.strategies.formulas.parser` — no reimplementation ✅
- No modifications to any existing strategy module files ✅

### Authentication & Ownership
- All 5 endpoints require `Depends(get_current_user)` ✅
- All endpoints verify strategy ownership via strategy.user_id ✅
- Returns 404 (not 403) to avoid information leakage ✅

### Database Design
- All 3 tables have proper FK constraints with CASCADE delete ✅
- Composite index (backtest_id, bar_index) on equity_curve for efficient queries ✅
- All financial columns use Numeric with appropriate precision ✅
- All DateTime columns use timezone=True ✅
- Models inherit from BaseModel (provides id, created_at, updated_at) ✅

---

## Issues Summary

### Blockers (must fix before PASS)
None

### Major (should fix before proceeding)
None

### Minor (note for future, does not block)
1. **Type annotation in models.py** — `symbols: Mapped[dict]` should be `Mapped[list]` since symbols is stored as a JSON array `["EUR_USD", "GBP_USD"]`. JSONB accepts both at runtime so this is purely a type hint issue, not a functional bug. Runtime code correctly iterates over it as a list.
2. **Linear window growth** — `bar_dicts[:bar_index + 1]` grows linearly in runner.py, meaning indicator computation near the end of a long backtest processes full history. For very large backtests (500K+ bars), a sliding window optimization could improve performance. Acceptable for V1.

---

## Risk Notes
- Synchronous execution could take >30 seconds for very large backtests (500K+ 1m bars across multiple symbols), potentially risking HTTP timeout. The task explicitly specifies synchronous design, so this is a known trade-off for V1.
- Sharpe ratio uses stdlib math instead of numpy — keeps dependencies minimal but could be slower for very large trade lists.
- Short position cash handling is simplified (no margin modeling) — sufficient for paper trading simulation.
- Drawdown/daily_loss events from TASK-039 emit on every check cycle rather than only on transitions; high event volume possible if backtest monitoring is added later.

---

## RESULT: PASS

Task is ready for Librarian update. The backtest engine is a well-structured, complete implementation covering all 22 acceptance criteria:

- 10 new files created in backend/app/backtesting/ + 1 migration
- 1 file modified (main.py router registration)
- Full bar replay engine with indicator warmup, 4 exit types, 4 position sizing types
- 27 performance metrics including Sharpe ratio, drawdown, profit factor
- 5 REST API endpoints with authentication, pagination, and downsampling
- All financial calculations use Decimal
- Reuses existing condition engine and indicator library without modification
- No frontend or studio files touched
