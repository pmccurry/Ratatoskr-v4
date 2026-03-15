# Builder Output — TASK-040

## Task
Backtest Engine (Backend)

## Completion Checklist
- [x] All deliverables created
- [x] All acceptance criteria addressed
- [x] No off-scope files created
- [x] No off-scope files modified
- [x] No locked decisions violated
- [x] Output follows naming conventions
- [x] Output follows folder structure conventions

## Files Created
- `backend/app/backtesting/__init__.py` — Empty module init
- `backend/app/backtesting/models.py` — BacktestRun, BacktestTrade, BacktestEquityPoint SQLAlchemy models
- `backend/app/backtesting/state.py` — BacktestState, BacktestTradeRecord, EquityPoint (in-memory state during backtest)
- `backend/app/backtesting/sizing.py` — Position sizing logic (fixed, fixed_cash, percent_equity, percent_risk)
- `backend/app/backtesting/metrics.py` — Performance metrics computation (win rate, Sharpe, drawdown, profit factor, etc.)
- `backend/app/backtesting/runner.py` — Core backtest engine with bar replay, condition evaluation, fill simulation
- `backend/app/backtesting/repository.py` — Database CRUD operations for backtest data
- `backend/app/backtesting/schemas.py` — Pydantic request/response schemas with camelCase aliases
- `backend/app/backtesting/router.py` — API endpoints (2 routers: backtest-scoped and strategy-scoped)
- `backend/migrations/versions/i9d0e1f2a3b4_create_backtest_tables.py` — Alembic migration for 3 tables

## Files Modified
- `backend/app/main.py` — Registered backtesting_router and strategy_backtest_router

## Files Deleted
None

## Acceptance Criteria Status
1. AC1: Alembic migration creates `backtest_runs`, `backtest_trades`, `backtest_equity_curve` tables — ✅ Done (migration chains from h8c9d0e1f2a3, includes all columns, FKs, indexes)
2. AC2: `POST /strategies/{id}/backtest` runs synchronously and returns complete results — ✅ Done (trigger_backtest endpoint creates run, executes runner, returns BacktestRunResponse)
3. AC3: Backtest runner walks bars chronologically and evaluates strategy conditions correctly — ✅ Done (chronological bar loop with condition_engine.evaluate() on sliding window)
4. AC4: Indicator warmup: loads extra bars before start_date, doesn't generate signals during warmup — ✅ Done (_load_bars fetches warmup bars before start_date, warmup_complete flag gates signal generation)
5. AC5: Fill simulation applies slippage and fees — ✅ Done (_simulate_fill adds 0.5 pip slippage, _calculate_fees applies 2 bps spread)
6. AC6: Stop loss exit works: position closes when bar low/high crosses SL price — ✅ Done (_check_exits handles SL for long and short with pip-based calculation)
7. AC7: Take profit exit works: position closes when bar high/low crosses TP price — ✅ Done (_check_exits handles TP for long and short)
8. AC8: Signal-based exit works: opposite signal closes existing position — ✅ Done (_process_entry closes opposite positions when signal_exit is true)
9. AC9: Time-based exit works: position closes after max_hold_bars — ✅ Done (_check_exits checks bar_index - entry_bar_index >= max_hold_bars)
10. AC10: Open positions force-closed at end of data with reason "end_of_data" — ✅ Done (after bar loop, remaining open positions closed with reason="end_of_data")
11. AC11: All 4 position sizing types work correctly — ✅ Done (sizing.py implements fixed, fixed_cash, percent_equity, percent_risk with JPY pip handling)
12. AC12: Performance metrics computed correctly — ✅ Done (metrics.py computes 25+ metrics including win rate, Sharpe, drawdown, profit factor, streaks, MFE/MAE)
13. AC13: Equity curve recorded at appropriate intervals — ✅ Done (every bar for 1h/4h/1d, every 10 bars for 1m, plus on trade events)
14. AC14: `GET /backtests/{id}` returns run details with metrics — ✅ Done
15. AC15: `GET /backtests/{id}/trades` returns trade list with pagination — ✅ Done (page/pageSize params, default 50 per page)
16. AC16: `GET /backtests/{id}/equity-curve` returns equity points with optional downsampling — ✅ Done (sample query param, ge=10, le=5000)
17. AC17: `GET /strategies/{id}/backtests` returns list of all backtests for strategy — ✅ Done (paginated, ordered by created_at desc)
18. AC18: Strategy config is frozen at backtest time — ✅ Done (config_version.config_json copied to backtest_run.strategy_config at creation)
19. AC19: Failed backtests store error message and set status to "failed" — ✅ Done (try/except in router catches exceptions, sets status="failed" and error=str(exc))
20. AC20: All financial calculations use Decimal (not float) — ✅ Done (state, sizing, runner all use Decimal; metrics converts to float only for final JSON output)
21. AC21: No frontend code modified — ✅ Done
22. AC22: Nothing inside /studio modified (except BUILDER_OUTPUT.md) — ✅ Done

## Assumptions Made
- Reused existing ConditionEngine and indicator library from strategies module (as instructed) — no modifications to those modules
- Sharpe ratio computed using per-trade returns (not per-bar), annualized using sqrt(min(trades, periods_per_year))
- Short positions use simplified cash handling (fees deducted, PnL settled on close) — no margin modeling
- JPY pairs use 0.01 pip value, all others use 0.0001
- Default slippage is 0.5 pips, default spread cost is 2 basis points
- All backtest endpoints require authentication and verify strategy ownership
- Equity curve downsampling always preserves the last data point

## Ambiguities Encountered
- The task spec shows `exit_config.signal_exit` for signal-based exits but the condition engine also evaluates `exit_conditions` from the strategy config. Both are implemented: `exit_conditions` triggers condition-based exits, `signal_exit` in exit_config triggers reversal on opposite entry signal.
- The task mentions reusing `FillSimulationEngine` but the backtest fill simulation is simpler (no broker interaction). Implemented inline fill simulation with slippage and fees rather than importing the paper trading fill engine.

## Dependencies Discovered
None — all dependencies (condition engine, indicator library, OHLCVBar model, BaseModel) already exist

## Tests Created
None — not required by this task

## Risks or Concerns
- For large backtests (e.g., 500K 1m bars across multiple symbols), the synchronous execution could take >30 seconds and risk HTTP timeout. The task specifies synchronous design, so this is deferred to a future async/background worker implementation.
- The bar window `bar_dicts[:bar_index + 1]` grows linearly, which means indicator computation for bars near the end processes the full history. For very long backtests, this could be slow. A sliding window optimization could be added later.
- No numpy dependency was added — Sharpe ratio uses stdlib math. This keeps dependencies minimal but could be slower for very large trade lists.

## Deferred Items
None — all deliverables complete

## Recommended Next Task
TASK-041: Frontend backtest UI (form to trigger backtests, results display with equity curve chart, trade table, metrics cards)
