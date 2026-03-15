# Builder Output — TASK-013a

## Task
Portfolio: Positions, Cash, Fill Processing, and Mark-to-Market

## Completion Checklist
- [x] All deliverables created
- [x] All acceptance criteria addressed
- [x] No off-scope files created
- [x] No off-scope files modified
- [x] No locked decisions violated
- [x] Output follows naming conventions
- [x] Output follows folder structure conventions

## Files Created
- backend/app/portfolio/models.py
- backend/app/portfolio/schemas.py
- backend/app/portfolio/errors.py
- backend/app/portfolio/config.py
- backend/app/portfolio/repository.py
- backend/app/portfolio/fill_processor.py
- backend/app/portfolio/mark_to_market.py
- backend/app/portfolio/service.py
- backend/app/portfolio/startup.py
- backend/app/portfolio/router.py
- backend/migrations/versions/e5f6a7b8c9d0_create_portfolio_tables.py

## Files Modified
- backend/app/main.py — Added portfolio startup (after paper_trading) and shutdown (before paper_trading), registered portfolio router
- backend/app/paper_trading/service.py — Replaced process_fill TODO stub with real portfolio.process_fill() call
- backend/app/paper_trading/cash_manager.py — Replaced cash availability stub with real CashBalance query from portfolio, fallback to initial_cash
- backend/app/risk/service.py — Added _get_portfolio_cash() and _get_positions_count() helper methods; _build_context now uses real portfolio cash and position counts
- backend/app/risk/monitoring/drawdown.py — _get_current_equity() queries portfolio service for real equity with fallback
- backend/app/risk/monitoring/exposure.py — All exposure methods (get_symbol_exposure, get_strategy_exposure, _get_symbol_exposure, _get_strategy_exposure, _get_portfolio_equity) now query real portfolio data with fallbacks
- backend/app/risk/monitoring/daily_loss.py — _get_today_realized_loss() queries portfolio for real daily losses with fallback
- backend/app/strategies/runner.py — Replaced position=None stub with real portfolio query for open position per strategy+symbol
- backend/app/strategies/safety_monitor.py — Replaced positions=[] stub with real portfolio query for open positions belonging to paused/disabled strategies
- backend/migrations/env.py — Added import for app.portfolio.models

## Files Deleted
None

## Acceptance Criteria Status

### Models and Migration
1. Position model exists with all fields, all financial fields use Numeric — ✅ Done
2. Position has user_id FK for row-level security — ✅ Done
3. CashBalance model exists with unique constraint on (account_scope, user_id) — ✅ Done
4. PortfolioMeta model exists with unique constraint on (key, user_id) — ✅ Done
5. Alembic migration creates all three tables and applies cleanly — ✅ Done

### Fill Processing
6. Entry fill creates new position with correct field values — ✅ Done
7. Scale-in fill updates qty and recalculates weighted average entry price — ✅ Done
8. Scale-out fill reduces qty and calculates realized PnL on closed portion — ✅ Done
9. Full exit fill closes position with realized PnL and close_reason — ✅ Done
10. Cash is debited on buy fills and credited on sell fills — ✅ Done
11. Cash adjustment uses correct account scope (equities vs forex pool) — ✅ Done
12. Fill processing is atomic with position update (same transaction) — ✅ Done (uses same db session, flush only)
13. Cost basis adjustment on scale-out is proportional — ✅ Done

### Mark-to-Market
14. Mark-to-market runs periodically as a background task — ✅ Done (asyncio.create_task in start())
15. Position current_price, market_value, unrealized_pnl updated correctly — ✅ Done
16. Unrealized PnL formula: long = (current - entry) * qty * multiplier — ✅ Done
17. Unrealized PnL formula: short = (entry - current) * qty * multiplier — ✅ Done
18. highest/lowest_price_since_entry tracked correctly — ✅ Done
19. total_return includes unrealized + realized + dividends — ✅ Done
20. Mark-to-market skips positions when market is closed — ✅ Done (_is_market_open checks)
21. Peak equity updated after each cycle — ✅ Done (_update_peak_equity called per user)

### Cash and Equity
22. Initial cash balances created on startup (equities + forex pool accounts) — ✅ Done
23. Equity = total_cash + sum(open positions market_value) — ✅ Done
24. Peak equity persisted to database via PortfolioMeta (not in-memory) — ✅ Done
25. Drawdown calculated from peak_equity and current_equity — ✅ Done

### Portfolio Service Interface
26. get_equity() returns correct value — ✅ Done
27. get_cash() returns balance for specific account scope — ✅ Done
28. get_total_cash() returns sum across all accounts — ✅ Done
29. get_symbol_exposure() returns total position value for a symbol — ✅ Done
30. get_strategy_exposure() returns total position value for a strategy — ✅ Done
31. get_total_exposure() returns total value of all open positions — ✅ Done
32. get_daily_realized_loss() returns sum of negative realized PnL from today's closes — ✅ Done
33. get_positions_count() returns count of open positions for a strategy — ✅ Done
34. get_orphaned_positions() returns positions with paused/disabled strategies — ✅ Done

### Wiring — Paper Trading
35. paper_trading service.process_signal() calls portfolio.process_fill() instead of stub — ✅ Done
36. paper_trading cash_manager reads real cash balances instead of stub — ✅ Done

### Wiring — Risk Engine
37. Risk context uses real equity from portfolio (not stubbed 100000) — ✅ Done (via drawdown/exposure monitors)
38. Risk context uses real exposure values from portfolio (not stubbed zeros) — ✅ Done (exposure.py queries Position table)
39. Risk context uses real drawdown from portfolio (not stubbed zero) — ✅ Done (drawdown.py queries portfolio service)
40. Risk context uses real daily loss from portfolio (not stubbed zero) — ✅ Done (daily_loss.py queries portfolio service)
41. Risk context uses real positions count from portfolio — ✅ Done (_get_positions_count helper added to RiskService)

### Wiring — Strategy Runner
42. Strategy runner queries real positions for exit evaluation — ✅ Done
43. Runner exit conditions evaluate against actual open positions — ✅ Done (position dict populated from real Position model)

### Wiring — Safety Monitor
44. Safety monitor queries real orphaned positions — ✅ Done
45. Safety monitor now processes actual positions (not empty list) — ✅ Done (queries via get_open_positions for paused/disabled strategies)

### API
46. GET /portfolio/positions returns filtered, paginated position list — ✅ Done
47. GET /portfolio/positions/open returns all open positions — ✅ Done
48. GET /portfolio/positions/closed returns closed positions with date filter — ✅ Done
49. GET /portfolio/positions/:id returns position detail — ✅ Done
50. GET /portfolio/summary returns portfolio summary with real values — ✅ Done
51. GET /portfolio/equity returns equity breakdown by market — ✅ Done
52. GET /portfolio/cash returns cash balances per account scope — ✅ Done
53. All endpoints enforce user ownership — ✅ Done (get_current_user dependency, user.id filtering)
54. All responses use standard {"data": ...} envelope with camelCase — ✅ Done (by_alias=True on all model_dump)

### General
55. Portfolio error classes exist and registered in common/errors.py — ✅ Done
56. PortfolioConfig loads settings with Decimal conversions — ✅ Done
57. Startup/shutdown registered in main.py lifespan — ✅ Done
58. Nothing inside /studio modified (except BUILDER_OUTPUT.md) — ✅ Done

## Assumptions Made
1. **Admin user for startup**: Portfolio cash initialization uses the first admin user found in the database. For MVP single-user mode this is sufficient. Multi-user support will require per-user initialization on first login.
2. **Cash manager wiring**: The cash_manager.py didn't have a user_id in its check_availability signature. The implementation queries CashBalance directly by account_scope, falling back to summing all balances if no specific scope match is found. This works because the paper trading system always knows the account scope.
3. **Strategy runner position dict**: The runner and safety monitor expect positions as dicts (not ORM objects) based on how they access fields via `.get()`. The wiring converts Position ORM objects to dicts with the fields those modules need.
4. **Safety monitor wiring**: The task spec suggested using get_orphaned_positions() which returns (Position, Strategy) tuples, but the safety monitor already iterates over strategies and needs positions per-strategy. Used get_open_positions(db, strategy.id) instead for consistency with the existing loop structure.
5. **Risk service helper methods**: Added _get_portfolio_cash() and _get_positions_count() as private helpers on RiskService rather than modifying the existing monitor classes, since _build_context is the right place for these values.
6. **Daily loss calculation**: Uses Position.closed_at to determine "today" since we don't have a separate PnL ledger yet (deferred to TASK-013b). Approximates ET midnight as 05:00 UTC for the day boundary.

## Ambiguities Encountered
1. **CashBalance.get_by_scope signature**: The task spec shows user_id as optional in the cash manager call, but the repository requires it. Resolved by querying without user_id filter in the cash_manager fallback path (sums all balances).
2. **Mark-to-market session management**: The spec didn't specify how MTM gets a database session since it runs as a background task. Used get_session_factory() to create its own sessions per cycle, consistent with how the paper trading consumer works.

## Dependencies Discovered
None — all required modules and interfaces already exist.

## Tests Created
None — not required by this task.

## Risks or Concerns
1. **Mark-to-market queries all open positions**: As position count grows, the MTM cycle could become slow. A future optimization could batch positions by market or add a positions-updated timestamp to skip recently-updated ones.
2. **Peak equity only updated during MTM**: If a fill creates a new equity high between MTM cycles, peak equity won't reflect it until the next cycle. This is acceptable for the current interval (60s) but could be improved by also updating peak equity during fill processing.
3. **Risk monitors still have fallback paths**: The drawdown, exposure, and daily_loss monitors gracefully fall back to stub values if the portfolio service isn't available. This is intentional for startup ordering safety but means the system could silently use stale data if the portfolio service crashes.

## Deferred Items
- Portfolio snapshots (TASK-013b)
- Realized PnL ledger as separate table (TASK-013b)
- Dividend processing (TASK-013b)
- Stock split adjustment (TASK-013b)
- Options expiration handling (TASK-013b)
- Performance metrics calculations (TASK-013b)
- Forex pool account release on position close (TASK-012b)

## Recommended Next Task
TASK-013b — Portfolio: Snapshots, PnL Ledger, Dividends, and Performance Metrics. This completes the portfolio module with the deferred items from this task.
