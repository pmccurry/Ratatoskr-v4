# Builder Output — TASK-011

## Task
Risk Engine Implementation

## Completion Checklist
- [x] All deliverables created
- [x] All acceptance criteria addressed
- [x] No off-scope files created
- [x] No off-scope files modified
- [x] No locked decisions violated
- [x] Output follows naming conventions
- [x] Output follows folder structure conventions

## Files Created
- backend/app/risk/models.py
- backend/app/risk/schemas.py
- backend/app/risk/config.py
- backend/app/risk/errors.py
- backend/app/risk/repository.py
- backend/app/risk/service.py
- backend/app/risk/evaluator.py
- backend/app/risk/startup.py
- backend/app/risk/router.py (replaced stub)
- backend/app/risk/checks/base.py
- backend/app/risk/checks/__init__.py (replaced empty stub)
- backend/app/risk/checks/kill_switch.py
- backend/app/risk/checks/strategy_enable.py
- backend/app/risk/checks/symbol.py
- backend/app/risk/checks/duplicate.py
- backend/app/risk/checks/position_limit.py
- backend/app/risk/checks/position_sizing.py
- backend/app/risk/checks/exposure.py
- backend/app/risk/checks/drawdown.py
- backend/app/risk/checks/daily_loss.py
- backend/app/risk/monitoring/drawdown.py
- backend/app/risk/monitoring/daily_loss.py
- backend/app/risk/monitoring/exposure.py
- backend/migrations/versions/c3d4e5f6a7b8_create_risk_tables.py

## Files Modified
- backend/app/main.py — Added risk module startup/shutdown in lifespan (start after signals, stop before signals)
- backend/app/common/errors.py — Added 5 new risk error codes to _ERROR_STATUS_MAP (RISK_EVALUATION_ERROR, RISK_CONFIG_NOT_FOUND, RISK_KILL_SWITCH_ALREADY_ACTIVE, RISK_KILL_SWITCH_NOT_ACTIVE, RISK_DECISION_NOT_FOUND)
- backend/migrations/env.py — Added import of app.risk.models for Alembic autogenerate

## Files Deleted
None

## Acceptance Criteria Status

### Models and Migration
1. RiskDecision model exists with all fields, unique constraint on signal_id — ✅ Done
2. KillSwitch model exists with scope/strategy_id fields and indexes — ✅ Done
3. RiskConfig model exists with all Numeric fields (never Float) — ✅ Done (Numeric(5,2) and Numeric(12,2))
4. RiskConfigAudit model exists for change tracking — ✅ Done
5. Alembic migration creates all four tables and applies cleanly — ✅ Done (c3d4e5f6a7b8)

### Check Pipeline
6. RiskCheck base class defines name, applies_to_exits, and evaluate interface — ✅ Done (abstract base class)
7. CheckResult supports PASS, REJECT, and MODIFY outcomes — ✅ Done (CheckOutcome enum)
8. RiskContext is loaded once and shared across all checks — ✅ Done (built in _build_context)
9. All 12 checks are implemented as separate classes — ✅ Done
10. Checks execute in the correct order (kill switch first, daily loss last) — ✅ Done (verified via get_risk_checks())
11. First rejection stops evaluation (remaining checks skipped) — ✅ Done (break on REJECT in evaluate_signal)
12. MODIFY outcome records changes and continues to next check — ✅ Done (all_modifications dict accumulates)
13. Exit signals skip non-applicable checks (kill switch, limits, exposure, drawdown, daily loss) — ✅ Done (applies_to_exits=False on 10 checks)
14. Exit signals only check symbol tradability and market hours — ✅ Done (_evaluate_exit_fast_path)
15. Exit signals are almost always approved (never blocked for risk reasons) — ✅ Done

### Individual Checks
16. Kill switch check blocks entries when active, allows exits — ✅ Done
17. Strategy enable check allows manual/safety/system source signals to bypass — ✅ Done
18. Symbol tradability checks watchlist — ✅ Done (via MarketDataService.is_symbol_on_watchlist)
19. Market hours check queues exits (modify), rejects entries — ✅ Done
20. Duplicate order check exists (stubbed — always passes until TASK-012) — ✅ Done
21. Position limit check uses strategy config max_positions — ✅ Done
22. Position sizing validates and caps at risk config max — ✅ Done (4 sizing methods: fixed_qty, fixed_dollar, percent_equity, risk_based)
23. Per-symbol exposure check can modify (reduce size) or reject — ✅ Done
24. Per-strategy exposure check rejects when exceeded — ✅ Done
25. Portfolio exposure check rejects when exceeded — ✅ Done
26. Drawdown check only blocks entries — ✅ Done
27. Daily loss check only blocks entries — ✅ Done

### Risk Decisions
28. Every evaluation creates a RiskDecision record — ✅ Done
29. Decision includes checks_passed list showing evaluation progress — ✅ Done
30. Decision includes portfolio_state_snapshot at decision time — ✅ Done (_build_portfolio_snapshot)
31. Modified decisions include modifications_json with original and adjusted values — ✅ Done
32. Signal status is updated after decision (risk_approved/rejected/modified) — ✅ Done (via SignalService.update_signal_status)

### Kill Switch
33. Global kill switch can be activated and deactivated via API — ✅ Done
34. Strategy-specific kill switch works independently — ✅ Done
35. Kill switch state persists across restarts (stored in database) — ✅ Done (kill_switches table)
36. Kill switch activation/deactivation is logged — ✅ Done (logger.info)

### Risk Configuration
37. Risk config is loaded from database (seeded with defaults on first run) — ✅ Done (seed_defaults in startup)
38. Risk config is editable via admin API — ✅ Done (PUT /risk/config, require_admin)
39. Every config change creates an audit record (field, old value, new value, who) — ✅ Done (per-field audit in update_risk_config)
40. All config values are Decimal (never Float) — ✅ Done (Numeric columns, Decimal in Python)

### Monitoring
41. Drawdown monitor calculates drawdown from peak equity — ✅ Done
42. Drawdown threshold status is correct (normal/warning/breach/catastrophic) — ✅ Done (warning at 70%, breach at 100%, catastrophic at catastrophic_percent)
43. Catastrophic drawdown auto-activates global kill switch — ✅ Done (in get_drawdown method)
44. Peak equity can be manually reset (admin only, logged) — ✅ Done (POST /risk/drawdown/reset-peak)
45. Daily loss monitor tracks realized losses (stubbed to zero until TASK-013) — ✅ Done
46. Daily loss resets at trading day boundaries — ✅ Done (_get_trading_day_boundaries)

### API
47. GET /risk/overview returns complete risk dashboard data — ✅ Done
48. GET /risk/decisions returns paginated, filtered decision list — ✅ Done
49. GET /risk/config returns current config — ✅ Done
50. PUT /risk/config updates config with audit trail (admin only) — ✅ Done
51. Kill switch endpoints work (activate, deactivate, status) — ✅ Done
52. GET /risk/exposure returns exposure breakdown — ✅ Done
53. GET /risk/drawdown returns drawdown state with threshold status — ✅ Done
54. POST /risk/drawdown/reset-peak resets peak equity (admin only) — ✅ Done
55. All responses use standard {"data": ...} envelope with camelCase — ✅ Done (all 12 endpoints)

### Integration
56. RiskEvaluator runs as background task consuming pending signals — ✅ Done
57. Approved signals have status updated to "risk_approved" — ✅ Done
58. Rejected signals have status updated to "risk_rejected" — ✅ Done
59. Modified signals have status updated to "risk_modified" — ✅ Done
60. Risk module registered in main.py lifespan (start after signals, stop before signals) — ✅ Done

### Stubs
61. Portfolio-related values in RiskContext are stubbed (zero/empty until TASK-013) — ✅ Done (portfolio_equity returns 100000, exposure returns 0/empty)
62. Duplicate order check is stubbed (always passes until TASK-012) — ✅ Done
63. Stubs are clearly marked with TODO comments referencing future tasks — ✅ Done

### General
64. Risk error classes exist and registered in common/errors.py — ✅ Done (5 error classes, 5 error codes added to map)
65. Nothing inside /studio modified (except BUILDER_OUTPUT.md) — ✅ Done

## Assumptions Made
1. Peak equity is tracked in-memory on the DrawdownMonitor instance (not persisted to DB). It initializes to current equity on startup and updates as equity changes. This is sufficient for MVP — a production system would persist peak equity to the database.
2. The RiskEvaluator interval uses `risk_evaluation_timeout_sec` (default 5s) as the polling interval for pending signals. This is a fast cycle appropriate for near-real-time signal processing.
3. The SymbolTradabilityCheck opens its own DB session to query the watchlist since the check receives only the signal and context (not a DB session). This is acceptable for MVP but could be optimized by pre-loading watchlist data into the context.
4. Position sizing estimation in exposure checks uses max_position_size_percent as a proxy for proposed position value since actual position sizing requires order data that doesn't exist yet (TASK-012/TASK-013).

## Ambiguities Encountered
1. The spec shows 12 endpoints in the router section but the risk overview response schema includes nested objects that could be represented as separate response schemas or inline dicts. Used separate Pydantic schemas for the top-level responses (RiskOverviewResponse, DrawdownResponse, ExposureResponse) and inline dicts for nested data to avoid excessive schema proliferation.
2. The spec doesn't specify whether the drawdown check in get_drawdown() should auto-activate the kill switch on every call or only during signal evaluation. Implemented it in get_drawdown() since the dashboard endpoint might be the first to detect catastrophic drawdown.

## Dependencies Discovered
None — all required modules (strategies, signals, market_data, auth, common) already exist.

## Tests Created
None — not required by this task

## Risks or Concerns
1. The SymbolTradabilityCheck creates its own DB session via get_session_factory(). This works but adds a DB connection per signal evaluation for this check. Consider pre-loading watchlist data into RiskContext in a future optimization.
2. Peak equity is in-memory only and resets to current equity on application restart. This means drawdown calculations may be incorrect after a restart if the peak was higher before. TASK-013 (portfolio module) should persist peak equity.
3. Exposure checks use estimated position values (max_position_size_percent * equity) rather than actual requested position values, since the position sizing calculation needs data from the paper trading module. These estimates are conservative.

## Deferred Items
None — all deliverables complete

## Recommended Next Task
TASK-012 — Paper Trading Module Implementation. The risk-to-paper-trading handoff is now in place (approved signals sit in risk_approved status). The paper trading engine needs to consume approved signals, create orders, simulate fills, and manage the executor abstraction.
