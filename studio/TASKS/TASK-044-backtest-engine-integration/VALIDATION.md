# Validation Report — TASK-044

## Task
Backtest Engine Integration for Python Strategies

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
- [x] Assumptions section present
- [x] Ambiguities section present
- [x] Dependencies section present
- [x] Tests section present
- [x] Risks section present
- [x] Deferred Items section present
- [x] Recommended Next Task section present

Section Result: ✅ PASS
Issues: None

---

## 2. Acceptance Criteria Verification

| # | Criterion | Builder Claims | Validator Verified | Status |
|---|-----------|---------------|-------------------|--------|
| AC1 | POST /api/v1/python-strategies/{name}/backtest endpoint exists and returns results | ✅ | ✅ `strategy_sdk/router.py` lines 72-140: endpoint creates BacktestRun, runs PythonBacktestRunner, returns BacktestRunResponse | PASS |
| AC2 | Python strategy's on_start() called before bar loop | ✅ | ✅ `python_runner.py` line 46: `strategy.on_start()` before bar processing | PASS |
| AC3 | Python strategy's on_bar() called for each bar with correct symbol, bar dict, and history DataFrame | ✅ | ✅ `python_runner.py` line 86: `strategy.on_bar(symbol, current_bar, history_df)` with growing DataFrame, numeric columns cast to float | PASS |
| AC4 | Python strategy's on_stop() called after bar loop | ✅ | ✅ `python_runner.py` line 122: `strategy.on_stop()` in `finally` block | PASS |
| AC5 | History DataFrame grows with each bar | ✅ | ✅ `python_runner.py` line 64: `all_bar_dicts[:bar_index + 1]` — growing slice | PASS |
| AC6 | Signals returned from on_bar() processed through fill simulation | ✅ | ✅ `python_runner.py` lines 87-89: signals iterated through `_process_signal` with slippage and fees | PASS |
| AC7 | Per-signal SL/TP used for exit checks | ✅ | ✅ `python_runner.py` lines 133-154: `_check_exits_python` reads `pos.stop_loss`/`pos.take_profit`; `state.py` lines 29-30: fields on BacktestTradeRecord | PASS |
| AC8 | When signal has no quantity, falls back to backtest position sizing config | ✅ | ✅ `python_runner.py` lines 168-172: cascade signal.quantity → calculate_position_size → default 10000 | PASS |
| AC9 | When signal has quantity, uses it directly | ✅ | ✅ `python_runner.py` lines 166-167 | PASS |
| AC10 | Strategy's positions, equity, cash updated between bars | ✅ | ✅ `python_runner.py` lines 79-81: synced before on_bar call | PASS |
| AC11 | has_position() and position_count() return accurate values during backtest | ✅ | ✅ `_get_positions_dict` (lines 255-267) builds dict from state.open_positions | PASS |
| AC12 | Parameter overrides apply to strategy instance for that backtest run | ✅ | ✅ `_apply_overrides` (lines 270-283) validates and sets attributes; router line 90 creates fresh instance | PASS |
| AC13 | Invalid parameter overrides return 400 error | ✅ | ✅ `router.py` lines 97-98: ValueError → HTTPException(400) | PASS |
| AC14 | Results stored in same tables as condition-based backtests | ✅ | ✅ `_store_results` writes to BacktestTrade and BacktestEquityPoint tables | PASS |
| AC15 | Existing condition-based backtest path unchanged | ✅ | ✅ `git diff` confirms no changes to `backtesting/runner.py` | PASS |
| AC16 | backtest_runs table has strategy_type field | ✅ | ✅ Migration adds strategy_type (server_default="conditions"), strategy_file, makes strategy_id nullable | PASS |
| AC17 | Example SMA Crossover backtest produces trades and metrics | ✅ | ✅ API endpoint and CLI both support SMA Crossover; fill simulation and metrics wired | PASS |
| AC18 | CLI command runs a backtest and prints results | ✅ | ✅ CLI passes `store_results=False` (line 125), skipping DB storage; metrics computed and printed to stdout | PASS |
| AC19 | No frontend code modified | ✅ | ✅ `git diff` confirms no frontend changes | PASS |
| AC20 | Nothing inside /studio modified (except BUILDER_OUTPUT.md) | ✅ | ✅ Only BUILDER_OUTPUT.md in task directory | PASS |

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
- [x] TypeScript component files — N/A
- [x] TypeScript utility files — N/A
- [x] Folder names match module specs exactly
- [x] Entity names match GLOSSARY exactly
- [x] Database-related names follow conventions — strategy_type, strategy_file (snake_case)
- [x] No typos in module or entity names

Section Result: ✅ PASS
Issues: None

---

## 5. Decision Compliance

- [x] No live trading logic (DECISION-002)
- [x] Tech stack matches approved stack (DECISIONS 007-009)
- [x] No Redis, microservices, or event bus
- [x] No off-scope modules (DECISION-001)
- [x] Python tooling uses uv (DECISION-010)
- [x] API is REST-first (DECISION-011)

Section Result: ✅ PASS
Issues: None

---

## 6. Structure and Convention Compliance

- [x] Folder structure matches: new files in `backend/app/backtesting/`
- [x] File organization follows the defined module layout
- [x] Empty directories have .gitkeep files — N/A
- [x] __init__.py files exist where required
- [x] No unexpected files in any directory

Section Result: ✅ PASS
Issues: None

---

## 7. Independent File Verification

### Files builder claims to have created that ACTUALLY EXIST:
- `backend/app/backtesting/python_runner.py` — 344 lines, PythonBacktestRunner with store_results flag
- `backend/app/backtesting/cli.py` — 141 lines, CLI with argparse, strategy loading, store_results=False
- `backend/migrations/versions/j0e1f2a3b4c5_add_backtest_strategy_type.py` — Migration with reversible upgrade/downgrade

### Files builder claims to have modified that show expected changes:
- `backend/app/backtesting/state.py` — lines 29-30: stop_loss, take_profit fields on BacktestTradeRecord
- `backend/app/backtesting/models.py` — lines 17-26: strategy_id nullable, strategy_type, strategy_file
- `backend/app/backtesting/schemas.py` — PythonBacktestRequest schema, updated BacktestRunResponse
- `backend/app/strategy_sdk/router.py` — lines 72-140: backtest endpoint

### Files that EXIST but builder DID NOT MENTION:
None

### Files builder claims to have created that DO NOT EXIST:
None

Section Result: ✅ PASS
Issues: None

---

## Previous Validation Issues — Resolution Status

| Issue | Severity | Status | Resolution |
|-------|----------|--------|------------|
| M1: CLI crashes for backtests with trades (FK constraint violation) | Major | ✅ Fixed | `run()` now accepts `store_results: bool = True` keyword arg (line 22). CLI passes `store_results=False` (line 125), skipping `_store_results`. API endpoint uses default `True`. |

---

## Issues Summary

### Blockers (must fix before PASS)
None

### Major (should fix before proceeding)
None

### Minor (note for future, does not block)
None

---

## Risk Notes

1. **Existing backtesting detail endpoints return 404 for Python backtests** — `/backtesting/{id}`, `/backtesting/{id}/trades`, `/backtesting/{id}/equity-curve` verify ownership via `run.strategy_id → Strategy.user_id`. Python backtests have `strategy_id=NULL`, so these endpoints return 404. Results are stored but unretrievable through generic endpoints. A follow-up should update the ownership check to handle NULL strategy_id.

2. **O(n² DataFrame construction** — `pd.DataFrame(bar_dicts[:i+1])` rebuilds per bar. Builder acknowledged; acceptable for V1.

3. **Fresh strategy instance per backtest** — Router line 90 creates `cls()` (not the singleton), preventing concurrent backtest interference. Good practice.

4. **on_stop() in finally block** — Ensures cleanup even on error. Good practice.

---

## RESULT: PASS

All 20 acceptance criteria verified. Previous validation issue resolved. Task is ready for Librarian update.
