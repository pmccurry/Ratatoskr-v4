# CHANGELOG

Append-only log of completed tasks. Each entry is added by the Librarian
after a task passes validation. Previous entries are NEVER edited.

---

## TASK-001 — Repository Scaffold
Date: 2026-03-12
Status: Complete
Summary: Created the full application scaffold for the Ratatoskr Trading Platform. Backend module structure (9 modules with sub-modules), frontend React/TypeScript scaffold, Docker Compose infrastructure, test directories, docs structure, and root project files. Structure and configuration only — no application logic beyond the /api/v1/health endpoint.
Files created: 113
Files modified: 0
Notes: npm install and uv lock must be run before Docker builds will work (expected for TASK-002). docker-compose.yml uses deprecated version field (cosmetic warning only). Builder output omitted vite-env.d.ts from file list but the file was created correctly.

## TASK-002 — Runnable Foundation
Date: 2026-03-12
Status: Complete
Summary: Made the TASK-001 scaffold runnable. Implemented the common module (config loading with all 93 env variables, async database sessions, SQLAlchemy base model with UUID/timestamps, domain error handling, shared schemas, UTC utility). Updated main.py with lifespan, CORS, exception handlers, all 8 module router stubs, and enhanced health check with DB connectivity. Initialized Alembic for async migrations. Ran npm install and uv lock. Created .env for local development.
Files created: 15
Files modified: 9
Notes: Config financial values use float (acceptable for config layer — must convert to Decimal at point of use in domain logic). Broker credential fields default to empty string (defers validation to module initialization). Lazy engine initialization pattern used to avoid import-time failures. CORS allows all origins for development.

## TASK-004 — Auth Module Implementation
Date: 2026-03-13
Status: Complete
Summary: Implemented the full auth module: User and RefreshToken models with Alembic migration, bcrypt password hashing, JWT access tokens with refresh token rotation, login/logout/refresh/change-password flows, get_current_user and require_admin FastAPI dependencies, user management endpoints (CRUD, suspend, unlock, reset password), admin seed script, and 9 DomainError subclasses. All 28 acceptance criteria verified.
Files created: 10
Files modified: 8
Notes: Replaced passlib[bcrypt] with bcrypt>=4.0.0 due to passlib incompatibility with Python 3.13 — identical security. OAuth2PasswordBearer returns non-envelope format for missing auth header (standard FastAPI behavior). Token reuse detection (revoke-all-on-reuse) deferred as hardening enhancement. Auth audit events deferred until observability module. TASK-003 (database foundation) was absorbed by TASK-002 and marked complete retroactively.

## TASK-005 — Market Data: Models, Schemas, and Broker Abstraction
Date: 2026-03-13
Status: Complete
Summary: Implemented the market data module data layer: 5 SQLAlchemy models (MarketSymbol, WatchlistEntry, OHLCVBar, BackfillJob, DividendAnnouncement) with Alembic migration, BrokerAdapter abstract base class with Alpaca and OANDA stubs, 5 repository classes (including PostgreSQL upsert for bars), MarketDataService with DB-backed methods implemented and broker-dependent methods as NotImplementedError, full router with DB-backed endpoints returning data and unimplemented endpoints returning 501, module config class, 4 error classes, and Pydantic schemas with camelCase aliases.
Files created: 10
Files modified: 3
Notes: Initial validation failed due to Mapped[float] type hints on financial fields — fixed to Mapped[Decimal] and re-validated. OHLCVBar inherits updated_at from BaseModel despite spec saying "NO updated_at" (acceptable trade-off vs. not inheriting from BaseModel). Error status codes corrected from pre-existing placeholder values (MARKET_DATA_STALE 422→503, MARKET_DATA_CONNECTION_ERROR 500→503).

## TASK-006 — Market Data: Universe Filter, Watchlist, Backfill, and Broker REST
Date: 2026-03-13
Status: Complete
Summary: Implemented full Alpaca and OANDA REST adapter logic (symbol listing, historical bars with pagination, option chain with Greeks, dividend fetching), rate limiter with sliding window, universe filter for equities (exchange/volume/price) and forex (configured pairs), backfill runner with per-symbol error handling and retry support, gap backfill function, corporate actions fetcher, option chain TTL cache, dividend yield calculation, and working /backfill/trigger, /watchlist/refresh, /options/chain endpoints. All 38 acceptance criteria verified.
Files created: 6
Files modified: 5
Notes: Added universe_filter_forex_pairs config field. httpx.AsyncClient created per request (simpler, can optimize later). OANDA sends both `to` and `count` params which may conflict — should validate against actual API. BackfillJob created as "running" instead of "pending" (no queue between creation and execution). float() used in filter_metadata_json (pragmatic for non-financial metadata). Module-level config evaluation in service.py could become fragile if import order changes.

## TASK-007 — Market Data: WebSocket Manager, Bar Storage, Aggregation, and Health
Date: 2026-03-13
Status: Complete
Summary: Completed the market data module. Implemented WebSocketManager with Alpaca (true WebSocket) and OANDA (HTTP chunked streaming with tick-to-bar accumulation) connections, exponential backoff reconnection with automatic gap backfill, BrokerWebSocket abstract base, BarProcessor with batched writes and aggregation triggers, AggregationEngine computing 5m/15m/1h/4h/1d from 1m bars only (not cascading), HealthMonitor with per-broker status/stale symbol detection/queue utilization/market hours awareness, startup/shutdown sequence registered in main.py lifespan, and live /health endpoint. Also fixed OANDA to/count parameter conflict from TASK-006. All 38 acceptance criteria verified.
Files created: 8
Files modified: 5
Notes: Initial validation failed due to aggregation engine window_end bug (replace(minute=N) raises ValueError for 1h) — fixed to use timedelta for all timeframes. OANDA volume=0 since pricing ticks don't carry volume. Market hours heuristic (UTC 13-21) is approximate — doesn't cover pre/after-market, holidays, half-days. AlpacaWebSocket.receive() uses recursion for non-bar messages (could accumulate stack frames). BarProcessor source field uses market name from stream vs broker name from backfill (inconsistent). This task completes Milestone 5 — Market Data Foundation.

## TASK-008 — Strategy: Indicator Library, Condition Engine, and Formula Parser
Date: 2026-03-13
Status: Complete
Summary: Implemented the strategy module computational engine. Built indicator library with 26 registered indicators across 6 categories (trend, momentum, volatility, volume, trend strength, price reference) using Decimal arithmetic throughout, condition engine with AND/OR/nested group evaluation supporting comparison/crossover/range operators with per-cycle caching, and safe formula parser with custom tokenizer/AST/evaluator (no eval/exec) supporting indicator functions, bar field references, arithmetic, and math functions. Added /strategies/indicators and /strategies/formulas/validate endpoints, 7 error classes, and module config. All 41 acceptance criteria verified.
Files created: 9
Files modified: 3
Notes: Formula validate() word splitting may miss operator-adjacent forbidden words (not a security issue — parser rejects at evaluation). `open` exists in both _FORBIDDEN and _BAR_FIELDS sets (checked in correct order). Shared _compute_directional_movement runs 3x when ADX/+DI/-DI called separately via formulas (mitigated by condition engine cache). Bollinger Bands uses population variance (standard convention).

## TASK-009 — Strategy: CRUD, Validation, Lifecycle, Runner, and Safety Monitor
Date: 2026-03-13
Status: Complete
Summary: Completed the strategy module. Implemented 5 SQLAlchemy models (Strategy, StrategyConfigVersion, StrategyState, StrategyEvaluation, PositionOverride) with Alembic migration, full CRUD with row-level security, config validation (completeness, indicators, params, formulas, risk sanity) with field-path errors and warnings, lifecycle state machine (draft→enabled→paused/disabled) with versioning (minor bump on enabled config edits, in-place for draft), strategy runner with timeframe alignment and parallel evaluation via asyncio.gather, safety monitor for orphaned positions (price-based exits only with position override support), and 16 REST endpoints. All 50 acceptance criteria verified across 3 validation rounds.
Files created: 9
Files modified: 3
Notes: Three validation fix rounds: (1) runner.py used b.timestamp instead of b.ts (OHLCVBar field mismatch), (2) camelCase aliases added to schemas but router model_dump() missing by_alias=True, (3) switched to alias_generator=to_camel and added by_alias=True to all 9 model_dump() call sites. PositionOverride.position_id has no FK (portfolio module not yet built — needs migration at TASK-013). Safety monitor positions list always empty until TASK-013. Runner uses single DB session for all strategies via asyncio.gather (potential contention under load). Market hours detection is UTC approximation. This task completes Milestone 6 — Strategy Engine, completing Phase 1.

## TASK-010 — Signals Module Implementation
Date: 2026-03-13
Status: Complete
Summary: Implemented the full signals module. Signal model with Numeric confidence and JSONB payload, Alembic migration, signal creation with validation (required fields, timestamp bounds, watchlist check) and deduplication (strategy entry/scale_in only, configurable window), lifecycle state machine (pending → risk_approved/rejected/modified/expired/canceled), background expiry checker with timeframe-based durations, 5 REST endpoints with ownership enforcement through strategy chain, and strategy integration (runner emits real signals, safety monitor emits source="safety" signals, pause/disable cancels pending signals). All 44 acceptance criteria verified across 2 validation rounds.
Files created: 11
Files modified: 6
Notes: Initial validation failed due to 4 of 5 router endpoints missing {"data": ...} envelope — fixed in v2. list_signals uses per-strategy iteration (N+1 pattern) which is suboptimal for users with many strategies. Signal validation queries strategy and watchlist on every creation (potential DB load under high signal volume). Pagination format differs slightly from strategies module (flat vs nested pagination object). Safety monitor signals never actually fire yet since positions list is still empty (TASK-013 dependency).

## TASK-011 — Risk Engine Implementation
Date: 2026-03-13
Status: Complete
Summary: Implemented the full risk engine. 4 SQLAlchemy models (RiskDecision, KillSwitch, RiskConfig, RiskConfigAudit) with Alembic migration, all 12 ordered risk checks as separate classes (kill switch, strategy enable, symbol tradability, market hours, duplicate order stub, position limit, position sizing with 4 methods, 3 exposure checks, drawdown, daily loss), exit signal fast path (only tradability + market hours), first-rejection-stops pipeline, MODIFY outcome accumulation, risk decision persistence with portfolio snapshots, background RiskEvaluator consuming pending signals, kill switch (global + per-strategy, DB-persisted), admin-editable risk config with per-field audit trail, drawdown monitor with threshold levels and catastrophic auto-kill-switch, daily loss monitor with trading day boundaries, and 12 REST endpoints. All 65 acceptance criteria verified in first validation round.
Files created: 24
Files modified: 3
Notes: Passed validation on first attempt — no fix rounds needed. Peak equity is in-memory only (resets on restart — TASK-013 should persist). SymbolTradabilityCheck opens its own DB session per evaluation (optimization opportunity). Exposure checks use estimated position values (max_position_size_percent * equity) since actual position data requires TASK-012/TASK-013. Duplicate order check stubbed (always passes) until TASK-012. Portfolio values stubbed to zero/defaults until TASK-013. monitoring/__init__.py not listed in builder output but exists and is required. This task completes Milestone 7 — Signals and Risk.

## TASK-012a — Paper Trading: Core Engine and Fill Simulation
Date: 2026-03-13
Status: Complete
Summary: Implemented the paper trading core engine. PaperOrder and PaperFill models (all financial fields Numeric) with Alembic migration, Executor abstract base class with SimulatedExecutor implementation, FillSimulationEngine with SlippageModel (configurable BPS per market, directional) and FeeModel (commission-free equities/options, spread-based forex), CashManager (stubbed to initial_cash until TASK-013), full order lifecycle (pending → accepted → filled/rejected), OrderConsumer background task polling every 2s, position sizing (4 methods), reference price fetching with timeframe fallback, risk engine duplicate order check wired to paper_orders table, and 6 REST endpoints. All 53 acceptance criteria verified in first validation round.
Files created: 16
Files modified: 4
Notes: Passed validation on first attempt. Signal status updates (order_filled/order_rejected) bypass SignalService and write directly to signal model — signal module's _VALID_TRANSITIONS doesn't include these transitions (should be added in future task). CashManager excludes fee estimate from required cash calculation (acceptable since cash is stubbed). _create_rejected_order uses fake UUID for risk_decision_id FK on unreachable error path (validator flagged as major but non-blocking). list_orders uses N+1 per-strategy query pattern. executors/__init__.py and fill_simulation/__init__.py exist but were not listed in builder output. TASK-012 split into 012a (this task) and 012b (forex pool, shadow tracking, Alpaca paper API).

## TASK-013a — Portfolio: Positions, Cash, Fill Processing, and Mark-to-Market
Date: 2026-03-13
Status: Complete
Summary: Implemented the portfolio core module. 3 models (Position with 30+ fields, CashBalance, PortfolioMeta) with Alembic migration, fill processor handling all 4 scenarios (entry, scale-in, scale-out, full exit) with atomic cash adjustments, mark-to-market background task with unrealized PnL, highest/lowest tracking, and peak equity persistence to PortfolioMeta, portfolio service with equity/cash/exposure/drawdown/daily-loss queries, initial cash seeding on startup, and 7 REST endpoints. Critically, this task wired real portfolio data into 5 previously-stubbed modules: paper_trading (process_fill, cash availability), risk (equity, exposure, drawdown, daily loss, positions count), strategy runner (real position queries for exits), and safety monitor (real orphaned position queries). All 58 acceptance criteria verified in first validation round.
Files created: 11
Files modified: 10
Notes: Passed validation on first attempt. cash_manager.py passes None as user_id for per-scope cash check (dead code, falls back to summing all balances — works for single-user MVP). DrawdownMonitor still maintains in-memory peak equity alongside the new DB persistence — risk check may see stale values after restart until MTM runs. runner.py has pre-existing avg_entry key mismatch (reads "avg_entry" but dict uses "avg_entry_price") — will break SL/TP calculations once real positions exist. Risk monitors query for admin user_id on every call (3 extra queries per evaluation). TASK-013 split into 013a (this task) and 013b (snapshots, PnL ledger, dividends, splits, performance metrics).

## TASK-012b — Paper Trading: Forex Pool, Alpaca Paper API, and Shadow Tracking
Date: 2026-03-13
Status: Complete
Summary: Completed the paper trading module. Implemented forex account pool with BrokerAccount and AccountAllocation models, per-pair allocation/release logic with FIFO netting compliance, ForexPoolExecutor routing forex orders through pool with "no_available_account" rejection, AlpacaPaperExecutor submitting real orders to Alpaca paper API with fill polling and SimulatedExecutor fallback, shadow tracking system (ShadowPosition, ShadowFill models) activating only on pool contention rejections with same slippage/fee models as real fills, ShadowEvaluator for exit condition checking, shadow mark-to-market, complete isolation from real portfolio/risk, runner integration for shadow exit evaluation (step 7b), and 5 new REST endpoints (pool status, accounts, shadow positions, detail, comparison). All 49 acceptance criteria verified in first validation round.
Files created: 10
Files modified: 6
Notes: Passed validation on first attempt. Unused variable in allocation.py (dead code). Shadow exit fill reuses entry signal_id (semantically misleading but functional). Shadow/forex-pool endpoints lack user_id filtering (single-user MVP acceptable). Runner accesses service._shadow_tracker private attribute. ForexPoolExecutor.submit_order adds optional db parameter not in base ABC. Alpaca fill polling uses synchronous sleep (future: WebSocket). Shadow positions accumulate indefinitely (needs cleanup/archival). This task completes TASK-012 and Milestone 8 — Paper Trading Engine.

## TASK-013b — Portfolio: Snapshots, PnL Ledger, Dividends, Splits, Options, and Metrics
Date: 2026-03-13
Status: Complete
Summary: Completed the portfolio module. 4 new models (PortfolioSnapshot, RealizedPnlEntry, DividendPayment, SplitAdjustment) with Alembic migration, periodic/event/daily-close snapshot manager with equity curve query, append-only realized PnL ledger with summary breakdowns (today/week/month/total) wired into fill processor, dividend processing (ex-date pending creation, payable-date cash credit with position tracking, income summaries), stock split adjustment (forward/reverse with unchanged cost basis and audit records), options expiration lifecycle (ITM intrinsic close, OTM worthless expiry), performance metrics calculator (total return, win rate, profit factor, Sharpe, Sortino, max drawdown, streaks — portfolio-wide and per-strategy), daily jobs orchestrator, and 12 new REST endpoints. All 52 acceptance criteria verified in first validation round.
Files created: 8
Files modified: 6
Notes: Passed validation on first attempt. Options expiration PnL entry records qty_closed=0 (position.qty zeroed before PnL entry creation — should capture qty first, as fill_processor correctly does). Admin endpoints operate on admin's own user_id only (single-user MVP). DailyPortfolioJobs class exists but has no automatic trigger wired. Sortino uses full-period denominator (common convention). Snapshot periodic loop discovers users from CashBalance table. This task completes TASK-013, Milestone 9 — Portfolio Accounting, and Phase 2 — Paper Trading MVP.

## TASK-014 — Observability Module Implementation
Date: 2026-03-14
Status: Complete
Summary: Implemented the full observability module. 4 models (AuditEvent as immutable/append-only, MetricDatapoint, AlertRule, AlertInstance) with Alembic migration, async EventEmitter with non-blocking queue (put_nowait), configurable batch writer with size/interval flush, priority-based overflow handling (drops debug/info, blocks for warning+), MetricsCollector gathering from portfolio/strategies/signals/paper_trading/system modules, AlertEngine evaluating 3 condition types (event_match, metric_threshold, absence) with cooldown and auto-resolve, NotificationDispatcher (dashboard DB, webhook httpx, email logged for MVP), 15 built-in alert rules seeded on startup (4 critical, 5 error, 6 warning), application logging with JSON/text formatters, observability starts first/stops last in lifespan, and 12 REST endpoints. All 58 acceptance criteria verified in first validation round.
Files created: 16
Files modified: 4
Notes: Passed validation on first attempt. get_event_emitter() returns Optional (safer than spec's non-optional signature). Warning+ events may block caller up to 1s during queue overflow (acceptable trade-off). Metric timeseries resolution parameter accepted but not implemented (raw datapoints returned). Batch writer drops events on write failure (no retry). Event emit() calls not yet wired into other modules' business logic (deferred incremental task). SMTP email deferred. This task completes Milestone 10 — Observability.

## TASK-015 — Frontend Shell, Routing, Auth, API Client, and Component Library
Date: 2026-03-14
Status: Complete
Summary: Implemented the complete frontend shell and foundation. AppShell with collapsible sidebar (6 trading + 2 admin nav items), alert banner with severity color-coding, status bar with connection dots and live clock. Auth flow with login page, AuthGuard, AdminGuard, token refresh with request queuing. Axios-based API client with Bearer token injection, envelope unwrapping, and 401 retry. 20 shared components (StatCard, DataTable with sorting/pagination, StatusPill, PnlValue, PriceValue, PercentValue, TimeAgo, ProgressBar, ChartContainer, ConfirmDialog, ActivityFeedItem, etc.). 9 TypeScript type definition files for all backend schemas. Formatters, constants, Zustand UI store. All 17 routes defined with placeholder pages and auth guards. All 61 acceptance criteria verified.
Files created: 62
Files modified: 3
Notes: Passed validation on first attempt. Forbidden page rendered inline in AdminGuard rather than as standalone component (documented assumption). StatusBar shows strategy status text instead of numeric count. StatusBar uses single marketData status for both Alpaca and OANDA. AuthLayout is a passthrough (Login page handles its own centering). PaginatedResponse type matches actual backend format rather than spec's nested pagination object. lucide-react added as dependency for sidebar icons.

## TASK-016 — Frontend: Dashboard Home View
Date: 2026-03-14
Status: Complete
Summary: Implemented the dashboard home view with 4 stat cards (equity, PnL, open positions, drawdown with progress bar) fetching from portfolio summary API, equity curve chart with Recharts AreaChart and period selector synced to Zustand, strategy status list with clickable items navigating to detail views, and activity feed with auto-scroll, hover pause, and severity/category filters. All data fetches use TanStack Query with configured refresh intervals. All 16 acceptance criteria verified.
Files created: 4
Files modified: 1
Notes: Passed validation on first attempt. Originally scoped as "strategy builder UI" in STATUS_BOARD, rescoped to "dashboard home view" during task packet creation. StrategyStatusList shows market+version instead of PnL+position count (strategy endpoint lacks PnL data). Today's PnL uses unrealizedPnl+realizedPnlTotal as approximation (no dedicated daily field). Activity feed category filter includes "execution" which doesn't match backend's "paper_trading" category. Activity feed fetches fixed 20 events with client-side filtering. Recharts adds >500KB bundle size (dynamic imports recommended for future). Completes Milestone 11 — Frontend Shell.

## TASK-018 — Frontend: Signals and Paper Trading Views
Date: 2026-03-14
Status: Complete
Summary: Implemented signals view with stats bar (6 metrics including color-coded approval rate), signal table with 8 columns and 5 filters, and signal detail panel. Implemented paper trading view with 4 tabs: order table with expandable detail panels, fill table with fee/slippage columns, forex pool status with account cards and pair capacity progress bars, and shadow tracking with shadow positions table and real-vs-shadow comparison with highlighted missed PnL. All data fetches use TanStack Query. All 28 acceptance criteria verified.
Files created: 7
Files modified: 2
Notes: Passed validation on first attempt. 1 major issue noted: text-danger class used in 4 files instead of text-error (undefined Tailwind class, causes unstyled sell-side text — fix is simple find-and-replace). Fill date range filter substituted with side filter (date picker not in shared library). Signal pagination uses client-side total. Order table lacks pagination controls. Strategy filter uses raw UUID text input instead of dropdown. No input debouncing on text filters. Shadow/forex-pool types defined locally instead of in shared types directory.

## TASK-019 — Frontend: Portfolio View
Date: 2026-03-14
Status: Complete
Summary: Implemented portfolio view with 4 tabs. Positions tab: summary stat cards, open positions table with 12 columns and close/SL/TP actions, collapsible closed positions section. PnL Analysis tab: summary cards (today/week/month/total), 30-day color-coded calendar heatmap with hover tooltip, win/loss distribution histogram. Equity tab: equity curve with period selector, drawdown chart with threshold line, equity breakdown (cash vs positions, equities vs forex). Dividends tab: income summary cards, upcoming dividends table, payment history table, by-symbol breakdown. All 27 acceptance criteria verified.
Files created: 8
Files modified: 1
Notes: Passed validation on first attempt. Close action is single button not dropdown (partial close requires quantity input, deferred). SL/TP dialog does not pre-fill current values. Closed positions use symbol filter instead of date range (no date picker component). PositionCard.tsx from task spec not created (functionality covered by other components). Equity curve missing YTD period option. ClosePositionDialog created but unused (PositionTable handles close internally). Win/loss histogram renders all bars in accent color instead of per-bucket green/red. Correct Tailwind classes used (no text-danger bug).

## TASK-017 — Frontend: Strategy List, Builder, and Detail Views
Date: 2026-03-14
Status: Complete
Summary: Implemented the most complex frontend feature set. Strategy list with filterable card grid and action buttons. Strategy builder with 9 form sections: identity, symbols (watchlist autocomplete), recursive condition builder with AND/OR groups, dynamic indicator parameters from API catalog, operator select (comparison/crossover/range), custom formula input, risk management (SL/TP/trailing), position sizing, debounced validation, and diff dialog for edit-mode saves. Strategy detail with 5 tabs: performance (stat cards, equity curve, metrics, closed trades), open positions with close/SL-TP actions, signals, readable config with version history, and evaluation log. All 43 acceptance criteria verified.
Files created: 11
Files modified: 3
Notes: Passed validation on first attempt. Evaluation row per-symbol expansion deferred (DataTable limitation). Open positions uses DataTable instead of cards (functionally equivalent). ClosePositionDialog and EditStopLossDialog inlined in StrategyDetail to avoid cross-feature dependency. ConditionRow is 353 lines (largest component — uses Math.random() for radio names, renders inline indicator select instead of importing IndicatorSelect/FormulaInput components). Diff detection limited to name/timeframe/SL/TP (conditions, symbols, sizing not compared). Correct Tailwind classes used throughout.

## TASK-020 — Frontend: Risk Dashboard, System Telemetry, and Settings
Date: 2026-03-14
Status: Complete
Summary: Implemented the final three frontend views. Risk dashboard: kill switch control with pulsing indicator and confirmation dialogs, 4 stat cards with progress bars (drawdown, daily loss, exposure, decisions), per-symbol and per-strategy exposure bar charts, risk decision table with expandable detail panels, read-only config summary. System telemetry: 5-tab layout with pipeline health status (colored dots, per-module list), throughput and latency metric cards, activity feed (reused from dashboard), background jobs table, database stats table. Settings: 5-tab layout with sub-route mapping, editable risk config form with confirmation dialog, user management (CRUD, suspend/activate, role changes), alert rule editor with enable/disable toggles and alert history with acknowledge, broker account status cards. All 35 acceptance criteria verified.
Files created: 13
Files modified: 3
Notes: Passed validation on first attempt. Risk config change history table deferred (no audit endpoint). Throughput sparklines deferred (no time-series metrics endpoint). Broker connection status hardcoded as "Connected" (paper trading platform). RiskConfigSummary has redundant "Edit in Settings" link. Settings tab handler navigates during render (mitigated with replace:true). RiskDecisionTable row click uses rowIndex (fragile). Correct Tailwind classes used throughout. This task completes Milestone 12 — Frontend Views, and Phase 3 — Dashboard and Operator Layer. All frontend views are now implemented.

## TASK-021 — Backend Bug Fixes
Date: 2026-03-14
Status: Complete
Summary: Fixed 8 bugs across 4 backend modules identified during previous validation rounds. FIX-B1: options expiration PnL entry now captures qty before zeroing position. FIX-B2: paper trading routes signal status updates through SignalService with proper state transitions. FIX-B3: DrawdownMonitor reads peak equity from portfolio service only (no stale in-memory fallback), returns "degraded" status when unavailable. FIX-B4: DailyPortfolioJobs auto-triggers after market close in snapshot periodic loop. FIX-B6: cash manager includes estimated fee in required cash for buy orders. FIX-B7: Sortino ratio denominator convention clarified with comment. FIX-B8: exposure checks use actual proposed position value from signal/strategy config instead of estimating from limit percentage. All 14 acceptance criteria verified.
Files created: 0
Files modified: 10
Notes: Passed validation on first attempt. No new features or modules — purely targeted bug fixes. Market close hour hardcoded to 21:00 UTC (1 hour late during EDT). DrawdownMonitor admin user lookup pattern repeated 3x in same file. Proposed position value is still an estimate when signal lacks qty (strategy config fallback). DailyPortfolioJobs instantiated per check (negligible overhead).

## TASK-022 — Frontend Bug Fixes
Date: 2026-03-14
Status: Complete
Summary: Fixed 16 frontend bugs and deleted 3 unused components. FIX-F1: all text-danger replaced with text-error (4 files). FIX-F2: ConditionRow radio buttons use useId() instead of Math.random(). FIX-F3: ActivityFeed category "execution" replaced with "paper_trading". FIX-F4: duplicate "Edit in Settings" link removed from Risk page. FIX-F5: StrategyStatusList shows StatusPill + last evaluated time. FIX-F6: EditStopLossDialog pre-fills current values. FIX-F7/F8: signal and order tables use server-side pagination totals. FIX-F9: strategy filters changed from UUID text input to dropdown. FIX-F10: fills tab date range filters added. FIX-F11: YTD added to equity curve period selector. FIX-F12: win/loss chart uses green/red per-bucket colors. FIX-F13: close position uses DropdownMenu. FIX-F14: risk config audit history table implemented. FIX-F15: sparklines deferred with TODO comment. FIX-F16: evaluation log expandable rows implemented. Deleted: IndicatorSelect.tsx, ClosePositionDialog.tsx, FormulaInput.tsx (all unused). All 23 acceptance criteria verified.
Files created: 0
Files modified: 18
Files deleted: 3
Notes: Passed validation on first attempt. No new features — purely targeted fixes and cleanup. Settings handleTabChange still called in render body (pre-existing from TASK-020, not in scope). Eval expand detail panel renders below DataTable not inline (DataTable limitation). FillTable still lacks pagination. EditStopLossDialog uses type cast to access position fields. Close Partial dropdown item is no-op with no disabled visual indicator. Risk config audit endpoint response shape assumed.

## TASK-023 — Docker Compose and Startup Polish
Date: 2026-03-14
Status: Complete
Summary: Production-ready Docker infrastructure and developer experience. Dockerfile.backend with uv multi-stage build running uvicorn on port 8000. Frontend Dockerfile with npm build + nginx serving with SPA fallback and /api/ reverse proxy. docker-compose.yml with 3 services (db postgres:16-alpine, backend, frontend), health checks, depends_on conditions, and named volume. Complete .env.example with all variables from cross_cutting_specs config catalog. Idempotent seed_admin.py with bcrypt password hashing. start-dev.sh with full lifecycle (db start, health wait, migrations, seed, backend+frontend with clean shutdown trap). README.md quickstart for both Docker Compose and local dev workflows. All 17 acceptance criteria verified.
Files created: 6
Files modified: 2
Notes: Passed validation on first attempt. No application code modified. Old Dockerfiles at infra/docker/ still exist (unused, not listed for deletion). start-dev.sh DATABASE_URL override may produce empty string if .env not sourced. start-dev.sh uses cd pattern instead of absolute paths. seed_admin.py doesn't handle missing users table. No .dockerignore created. python-dotenv soft dependency in seed script.

## TASK-024 — Frontend Visual Fix-Up
Date: 2026-03-14
Status: Complete
Summary: Hardened the frontend against null/undefined data crashes. Added toNumber() helper and null-guarded all 9 formatter functions to return em dash for bad inputs. Created ErrorBoundary component with two-level wrapping: global (AppShell outlet) and per-widget (Dashboard). Added optional chaining and null-coalescing across Dashboard StatCards, Portfolio equity breakdown, Risk stat cards/exposure/decisions, and Settings tab navigation. Fixed Settings render-time navigate anti-pattern with onTabChange callback. Fixed StrategyBuilder missing key field, client-side validation, and dict error parsing. All 16 acceptance criteria verified.
Files created: 1
Files modified: 11
Notes: Passed validation on first attempt. No backend code modified. formatPnl and formatPercent lose negative sign for negative values (display bug, not crash — recommend follow-up fix). Strategy key auto-generated from name slugification (collision risk on similar names, backend enforces uniqueness). New strategy validation is client-side only (no POST /strategies/validate endpoint). NotFound page already existed — no changes needed.

## TASK-025 — Integration Verification and Hardening
Date: 2026-03-14
Status: Complete
Summary: Fixed formatPnl/formatPercent negative sign bug from TASK-024. Hardened CORS with configurable origins (not hardcoded "*"), added JWT secret production guard (RuntimeError if default secret used in production, warning in development). Added ENVIRONMENT and CORS_ALLOWED_ORIGINS to config and .env.example. Created .dockerignore at repo root and frontend/. Deleted stale Dockerfiles at infra/docker/ (replaced by TASK-023). Verified migration chain integrity (10 migrations, all links valid). Confirmed startup/shutdown order with documented deviation (observability starts first for event emitter availability). Verified global exception handler, background task resilience, and graceful shutdown. All 18 acceptance criteria verified.
Files created: 2
Files modified: 5
Files deleted: 3
Notes: Passed validation on first attempt. Many ACs were "already correct" (verified existing behavior). Migration chain verified by inspection only (no live Postgres). Startup order deviates from spec: observability starts first instead of 10th — intentional and correct since other modules emit events during startup. Migration filenames don't match internal revision IDs (cosmetic, Alembic uses internal IDs). Health endpoint doesn't report broker status (acceptable for MVP).

## TASK-026 — Test Infrastructure + Strategy Module Unit Tests
Date: 2026-03-14
Status: Complete
Summary: Set up pytest infrastructure and wrote comprehensive unit tests for the strategy module's core logic. Configured pytest in pyproject.toml, created root conftest.py with make_bars/make_trending_bars/make_flat_bars helpers using Decimal values and timezone-aware timestamps, and wrote 175 pure unit tests across 4 test files: indicator library (73 tests covering all 11 MVP indicators plus 8 additional), condition engine (33 tests covering all 9 operators and AND/OR group logic), formula parser (36 tests covering valid expressions, invalid expressions, and injection prevention), and strategy validation (33 tests covering valid configs, invalid configs, risk sanity, and multi-output). All tests use Decimal for financial values and require no database or network.
Files created: 7
Files modified: 1
Notes: Passed validation on first attempt. Two minor issues: crosses_below operator has only 1 test case (AC5 requires 2 minimum — low risk since symmetric with crosses_above which has 3). Builder per-file test counts in BUILDER_OUTPUT.md were slightly inaccurate (67/32/34/42 reported vs 73/33/36/33 actual) but total of 175 is correct. Known application bug: formula parser resolves bare `volume` identifier to close price (out of scope, documented for future fix).

## TASK-027 — Unit Tests: Trading Pipeline (Risk, Fills, PnL, Signals, Forex Pool)
Date: 2026-03-14
Status: Complete
Summary: Wrote 127 new unit tests across 5 test files for the trading pipeline's core logic. Risk checks (41 tests covering 9 of 12 checks — 3 DB-dependent checks deferred to integration tests) with pipeline ordering and exit signal exemption verification. Fill simulation (22 tests for slippage, fees, and net value with per-market configs). PnL calculations (33 tests covering all 4 fill-to-position scenarios, weighted average entry, realized/unrealized PnL for long and short positions). Signal dedup/expiry (21 tests covering window-based dedup, all 4 exempt sources, and TTL expiry). Forex pool allocation (10 tests for account allocation, contention rejection, release, and multi-pair). All tests use Decimal and are pure unit tests with mocked dependencies. Total suite: 302 passed in 0.62s.
Files created: 5
Files modified: 0
Notes: Passed validation on first attempt. 3 of 12 risk checks (SymbolTradability, MarketHours, DuplicateOrder) not unit-tested because they create internal DB sessions — documented for integration tests (TASK-028). Some PnL tests verify math formulas directly rather than calling async DB-dependent process_fill(). Builder per-file test counts slightly inaccurate (same pattern as TASK-026) but total of 127 is correct. MockRiskConfig mirrors real model fields and will need updating if model changes.

## TASK-028 — Integration Tests (Database-Backed)
Date: 2026-03-14
Status: Complete
Summary: Wrote 60 database-backed integration tests across 6 test files with shared conftest. Created integration conftest with session-scoped test database engine (create_all/drop_all), per-test session rollback isolation, and 5 entity fixtures (admin_user, regular_user, sample_strategy, draft_strategy, sample_position). Tests cover: strategy CRUD and lifecycle (10 tests), signal creation and transitions (11 tests), all 4 position fill types with user isolation (12 tests), risk evaluation with kill switch persistence (10 tests), bar storage and OHLCV aggregation rules (9 tests), and dividend/stock split processing (8 tests). All financial values use Decimal. Total test suite: 362 tests (302 unit + 60 integration).
Files created: 8
Files modified: 0
Notes: Passed validation on first attempt. Five minor gaps vs task spec: signal dedup and invalid transition not tested at integration level (covered by TASK-027 unit tests), user modify isolation only tests "see" not "modify", bar upsert behavior not tested, several spec-defined edge cases replaced with alternative coverage (catastrophic drawdown → kill switch persistence, 1m-to-1h aggregation → SQL aggregate verification, split adjusts open orders → not present). Risk evaluation tests reuse unit test mocks for check-level tests with only KillSwitchPersistence using real DB fixtures. Bar aggregation tested via SQL aggregates rather than aggregation engine pipeline. Integration tests require running PostgreSQL with trading_platform_test database.

## TASK-029 — E2E API Flow Tests
Date: 2026-03-14
Status: Complete
Summary: Wrote 68 end-to-end API tests across 6 test files exercising the full FastAPI application via httpx AsyncClient with ASGITransport (no live server). Created E2E conftest with unauthenticated and authenticated client fixtures, admin user seeding with bcrypt. Tests cover: auth flow with login/refresh/logout/protected routes (11 tests), strategy CRUD and lifecycle (11 tests), signal/order/fill/portfolio read endpoints (14 tests), manual close and position endpoints (5 tests), risk endpoints with kill switch round-trip and config audit (11 tests), and API conventions including response envelope, pagination, error format, camelCase, and health endpoint (16 tests). Total test suite: 430 tests (302 unit + 60 integration + 68 E2E).
Files created: 8
Files modified: 0
Notes: Passed validation on first attempt. First task with no per-file test count discrepancy. Two minor gaps: delete-enabled-strategy test not implemented, manual close tests mostly verify read endpoints rather than close operations (close requires pre-existing positions from full pipeline or DB fixtures — only nonexistent position 404 tested). Some error response tests are conditional (500 test only checks format if 500 occurs). Risk evaluation tests for checks 1-9 reuse unit test mocks. E2E tests require PostgreSQL and full app startup (lifespan events). Session-scoped database means kill switch tests must clean up after themselves.

## TASK-030 — Frontend Unit Tests (Vitest)
Date: 2026-03-14
Status: Complete
Summary: Set up vitest testing infrastructure and wrote 112 frontend unit tests across 11 test files. Configured vitest with jsdom environment in vite.config.ts, created setup file with @testing-library/jest-dom matchers and matchMedia mock, added dev dependencies (vitest, @testing-library/react, jest-dom, user-event, jsdom). Tests cover: all 9 formatter functions with 60 tests (null/undefined/NaN guards, sign verification for PnL and percent, em dash returns), Zustand UI store (7 tests for sidebar, equity curve period, activity feed), and 8 shared components — StatusPill (9 color mapping tests), PnlValue (6 tests), PercentValue (5 tests), PriceValue (4 tests), EmptyState (4 tests), ErrorBoundary (5 tests), ErrorState (4 tests), TimeAgo (4 tests), plus AuthGuard (4 tests with route mocking). All 112 tests pass in 1.64s. Total test suite: 542 tests.
Files created: 12
Files modified: 2
Notes: Passed validation on first attempt. Per-file test counts all match exactly. Three minor gaps: PnlValue, TimeAgo, and PriceValue missing null render tests at component level (null-guard logic tested at formatter level). Some component tests use container.innerHTML.toContain() for Tailwind class checking (fragile if class names change). vitest default script runs in watch mode — CI should use `vitest run`.

## TASK-031 — Playwright Browser E2E Tests
Date: 2026-03-14
Status: Complete
Summary: Set up Playwright testing infrastructure and wrote 43 browser E2E tests across 6 spec files. Configured Playwright with chromium, webServer auto-start, sequential execution, and trace-on-retry. Created reusable login helper with accessible selectors. Tests cover: auth flow (5 tests — login form, dark theme, valid login, wrong password, redirect), navigation (10 tests — sidebar items, 8 parameterized route renders, 404 page), dashboard (7 tests — title, stat cards, strategy status, activity feed, no blank screen, dark theme, no console errors), strategy builder (8 tests — list, new button, navigate, form sections, fill name, market radios, timeframe, save button), risk dashboard (4 tests — renders, title, kill switch visible, config section), and smoke tests (9 tests — 8 parameterized route console error checks, no white flash). Total test suite: 585 tests across all layers.
Files created: 8
Files modified: 1
Notes: Passed validation on first attempt. Per-file test counts all match exactly. Five minor gaps: save-to-list flow not fully tested (requires backend API), logout test not implemented, kill switch activate/deactivate interaction not tested (only visibility), sidebar collapse/expand not tested, chart area not explicitly tested. Some tests use waitForTimeout (2000-3000ms) which may be fragile in slow environments. Console error filtering is permissive to avoid flaky tests. Tests require full stack (backend + PostgreSQL + frontend). npx playwright install chromium required before first run. This task completes Milestone 13 — Testing and Validation.

## TASK-032 — Alpaca Broker Connectivity & Real Data Pipeline
Date: 2026-03-14
Status: Complete
Summary: Verified and hardened the Alpaca broker integration via comprehensive code review. Fixed 3 bugs: unbounded recursion in AlpacaWebSocket.receive() (returned None instead of recursive call for non-bar batches), broker fallback boolean check in paper trading executor (truthy string always enabled fallback — now checks for explicit disable values), and inline asyncio import moved to module top level. Enhanced health endpoint to report broker connection status from WebSocket manager. Added Operations Runbook to README with Alpaca/OANDA setup instructions and troubleshooting. All verification was code review only — no live API keys available.
Files created: 0
Files modified: 5
Notes: Passed validation on first attempt. One major issue noted but not blocking: health endpoint key mismatch — main.py reads `subscribed_symbols` (snake_case) but ConnectionHealth.to_dict() returns `subscribedSymbols` (camelCase), causing subscribed symbol count to always show 0. Status field works correctly. Minor: receive() returning None for non-bar batches triggers unnecessary reconnection in WebSocket manager (strictly better than original recursion crash). WebSocket ConnectionClosed vs ConnectionClosedError import may need adjustment with websockets library version changes. Live testing required with real API keys during market hours for full verification.

## TASK-033 — OANDA Forex Connectivity & Real Account Pool Mapping
Date: 2026-03-14
Status: Complete
Summary: Verified OANDA forex integration and implemented real account pool mapping infrastructure. Added 8 config settings for OANDA pool sub-account mapping (4 account IDs + 4 tokens), rewrote pool manager `seed_accounts()` to load real OANDA account mappings from environment with mixed virtual/real mode support, updated .env.example with pool variables, and expanded README with OANDA connectivity and forex pool runbook. OANDA streaming adapter (HTTP chunked transfer with tick-to-bar accumulation), REST adapter, and shadow tracker verified as structurally correct via code review. Forex executor still uses internal simulation per DECISION-002 — real OANDA order submission deferred.
Files created: 0
Files modified: 4
Notes: Passed validation on first attempt. No bugs found — existing OANDA implementations were correct. Four minor issues: pool seed_accounts() doesn't properly handle virtual→real account transitions (orphaned records), OANDA adapter has inline asyncio import (same pattern fixed in Alpaca during TASK-032), shadow exit fee uses manual calculation vs entry's full fill engine (~15 bps asymmetry), no live testing performed (code review only). Pool account mapping is additive infrastructure — prepares for real OANDA sub-account routing without changing existing simulation behavior.

## TASK-034 — Audit Trail Verification & Trade Reconciliation
Date: 2026-03-14
Status: Complete
Summary: Verified and completed the audit event chain for the signal-to-fill pipeline. Added 4 event emission points (signal.created, signal.status_changed in signals service; risk.evaluation.completed in risk service; paper_trading.order.filled in paper trading service) with emoji-prefixed summaries per DECISION-024. Created signal trace endpoint (GET /signals/{id}/trace) that collects related entity IDs through FK relationships and returns chronological audit events with duration. Created broker reconciliation endpoint (GET /paper-trading/reconciliation) comparing internal positions against Alpaca REST API and OANDA REST API with unconfigured/error handling. Verified event immutability — no update/delete paths exist in repository or API.
Files created: 1
Files modified: 5
Notes: Passed validation on first attempt. Four minor issues: unused require_admin import in reconciliation endpoint, partial event coverage (4 of ~15 specified event types now emitted — remaining deferred), OANDA reconciliation lacks qty/side mismatch comparison (only presence/absence), reconciliation uses float() for qty comparison instead of Decimal. Remaining event emissions (strategy evaluation, portfolio position, kill switch, order creation) documented as deferred items — infrastructure pattern established by this task.

## TASK-035 — Pre-Live Readiness Checklist & Deployment Hardening
Date: 2026-03-14
Status: Complete
Summary: Implemented deployment hardening and automated readiness verification. Added in-memory sliding window rate limiter (no Redis per DECISION-004) with 3 endpoint configurations: login (5/60s), refresh (10/60s), password change (3/60s) wired as FastAPI dependencies returning 429 with structured errors. Added request body size limit middleware (1MB default, configurable) returning 413. Added JSON logging formatter for production (`LOG_FORMAT=json`). Created `scripts/readiness_check.py` with 14 automated checks across security (JWT secret, admin password, CORS, .gitignore, sensitive logs), config (environment), connectivity (database, Alpaca, OANDA), broker (pool mapping, kill switch), and database (migrations) — exits 0 on pass, 1 on failure. Added pre-live checklist to README with automated, manual review, and security sections. Verified sensitive data never appears in logs.
Files created: 3
Files modified: 5
Notes: Passed validation on first attempt. Five minor issues: rate limit env variables missing from .env.example (hardcoded instead of configurable), password change rate limit uses per-IP instead of per-user, check_sensitive_logs is a no-op (returns pass immediately), check_kill_switch always returns warn (no auth), rate limiter memory growth on long-running instances. This task completes Milestone 14 — Live Trading Preparation, Phase 4 — Hardening and Live Preparation, and the entire MVP roadmap (Phases 1–4, Milestones 1–14, TASK-001 through TASK-035).

## TASK-036 — Live Connectivity Verification & Post-Hardening Bug Fixes
Date: 2026-03-14
Status: Complete
Summary: Fixed all 11 bugs identified by Validators across TASK-032 through TASK-035. BF-1: health endpoint `subscribedSymbols` key mismatch (always showed 0). BF-2: Alpaca WebSocket `receive()` internal loop prevents false reconnection on non-bar messages. BF-3: forex pool `seed_accounts()` uses slot-based lookup to prevent orphaned records on virtual-to-real transitions. BF-4: OANDA adapter `import asyncio` moved to module top level. BF-5: shadow exit fees now use `FeeModel.calculate()` matching entry path. BF-6: reconciliation endpoint changed to admin-only via `require_admin`. BF-7: OANDA reconciliation now checks qty/side mismatches (not just presence/absence). BF-8: all reconciliation qty comparisons use `Decimal` instead of `float`. BF-9: rate limit values configurable via 6 env vars + Settings class with lazy-init. BF-10: `check_sensitive_logs` now scans Python files for logger lines with sensitive patterns. BF-11: `check_kill_switch` authenticates and checks real kill switch state.
Files created: 0
Files modified: 11
Notes: Passed validation on first attempt with zero issues — all 11 bugs cleanly resolved. Live broker connectivity not tested (no API keys in build environment) — verified via code review. All fixes verified against original Validator reports. Platform is ready for live testing with real broker API keys.

## TASK-036a — Fix Alpaca Universe Filter
Date: 2026-03-14
Status: Complete
Summary: Fixed the Alpaca adapter's blanket 404 handler in `_request()` that treated all 404 responses as symbol-not-found errors. The `/v2/assets` endpoint returning 404 (due to invalid keys or API issues) raised `SymbolNotFoundError("assets")` instead of a proper connection error, producing the misleading log "Symbol 'assets' not found" and blocking the entire data pipeline (no symbols → empty watchlist → no WebSocket subscriptions → no market data). Fix distinguishes symbol-specific endpoints (`/stocks/`, `/instruments/`) from management endpoints, raising `MarketDataConnectionError` with the actual response text for non-symbol 404s.
Files created: 0
Files modified: 1
Notes: Passed validation on first attempt. One minor issue: heuristic for symbol-specific endpoints (`/stocks/`, `/instruments/` path check) may miss future endpoint patterns like `/v2/options/{symbol}`, but fallback is a more descriptive `MarketDataConnectionError` rather than a wrong `SymbolNotFoundError`.

## TASK-036b — Fix OANDA Backfill Count Limit & DB Transaction Cascade
Date: 2026-03-15
Status: Complete
Summary: Fixed two related bugs discovered during first live OANDA connectivity. Fix 1: OANDA `fetch_historical_bars()` now uses `from` + `count` (capped at 5,000) instead of `from` + `to`, with proper pagination that advances `current_start` past the last candle, filters candles past the requested `end`, and terminates early when fewer than max candles returned. Fix 2: each symbol/timeframe backfill now runs in its own isolated DB session via `session_factory()`, so an API error or DB failure in one backfill doesn't poison the SQLAlchemy session for subsequent symbols. On error, the session is rolled back and the job status is updated to "failed" in a fresh transaction before continuing.
Files created: 0
Files modified: 2
Notes: Passed validation on first attempt. Two minor issues: `needs_backfill()` still uses original startup `db` session (read-only, safe but inconsistent), and `backfill_gap()` lacks the same session isolation (called from WebSocket reconnect path, not startup). Risk note: job object re-attachment after rollback via `backfill_db.add(job)` could be fragile if the job had relationships.

## TASK-036c — Fix Greenlet Spawn Error in Paginated Backfill
Date: 2026-03-15
Status: Complete
Summary: Fixed `greenlet_spawn has not been called` error that hit all 1m and 1h OANDA backfills (20 of 40 jobs). Root cause: after committing the BackfillJob object and running a long multi-page `fetch_historical_bars()`, accessing ORM attributes like `job.status = "completed"` triggered an implicit synchronous refresh in SQLAlchemy's async driver. Fix 1: capture `job_id` immediately after creation, then use raw `UPDATE` statements (`update(BackfillJob).where(BackfillJob.id == job_id).values(...)`) for both success and error paths instead of ORM attribute access. Fix 2: batched upsert at 1,000 bars per batch instead of single massive INSERT for up to 43,200 bars.
Files created: 0
Files modified: 1
Notes: Passed validation on first attempt. Two minor issues: `from sqlalchemy import update` inside function body instead of module-level imports, and `backfill_gap()` still uses single upsert without batching (acceptable for small gap backfills). Risk note: inner try/except with `pass` silently swallows job status update failures in the error path.

## TASK-037 — VPS Deployment (DigitalOcean + Docker Compose + SSL)
Date: 2026-03-15
Status: Complete
Summary: Created complete VPS deployment infrastructure for DigitalOcean. 7 files created: `scripts/server-setup.sh` (Docker install, ufw firewall 80/443/SSH, 2GB swap, ratatoskr app user), `docker-compose.prod.yml` (5 services: postgres:16-alpine, backend, frontend, nginx:alpine, certbot with auto-renewal every 12h — only nginx exposes ports), `nginx/prod.conf.template` (HTTP→HTTPS redirect, TLS 1.2/1.3, security headers including HSTS/X-Frame-Options/X-Content-Type-Options, `/api/` proxy to backend, `/` proxy to frontend SPA, gzip), `nginx/init.conf` (HTTP-only bootstrap for ACME challenge), `.env.production.example` (186 lines, all config variables with production defaults, CHANGE_ME placeholders for secrets), `scripts/deploy.sh` (env validation, envsubst nginx config, SSL bootstrap flow with init.conf→certbot→restore, docker compose build, health wait loop, alembic migrate, admin seed), `scripts/update.sh` (git pull, rebuild, migrations). 3 files modified: frontend Dockerfile (VITE_API_BASE_URL build arg), README (deployment section), .gitignore (generated files).
Files created: 7
Files modified: 3
Notes: Passed validation on first attempt. Three minor issues: README uses generic placeholders instead of real IP/domain (better for maintainability), deploy.sh seed uses inline Python import (fragile but functional), update.sh uses sleep 10 instead of health check loop. Risks: Let's Encrypt rate limits during failed bootstraps, database password in DATABASE_URL env var, single point of failure (mitigated by restart: unless-stopped).

## TASK-038 — Live Site Bug Fixes (Health, Status Bar, Missing Endpoints, Dashboard)
Date: 2026-03-15
Status: Complete
Summary: Fixed 8 bugs discovered on the live production site. BF-1: module health checks now use correct getter names (`get_ws_manager` for market_data, `get_runner` for strategies) instead of non-existent functions. BF-2: added `GET /observability/jobs` endpoint aggregating 7 background task runner statuses via dynamic import + getter pattern, plus backfill progress from `backfill_jobs` table. BF-3: added `GET /observability/database/stats` endpoint querying `pg_stat_user_tables` for row counts and `pg_total_relation_size()` for table sizes. BF-4: wired `/settings/system` route and `pathToTab()` handler. BF-5: status bar now reads per-broker status from `/health` endpoint with nuanced labels (Connected/Not configured/No symbols/Disconnected). BF-6: WebSocket alert false positive partially addressed (status bar fixed, full alert rule suppression deferred). BF-7: portfolio summary returns `PAPER_TRADING_INITIAL_CASH` ($100k) as equity/cash when no portfolio data exists. BF-8: backfill progress (completed/failed/running/total) included in jobs endpoint.
Files created: 0
Files modified: 6
Notes: Passed validation on first attempt. Three minor issues: BF-6 alert rule suppression deferred (requires alert evaluator market-hours awareness), database stats computes total_size but doesn't return it, portfolio summary uses float() for initial cash instead of Decimal (read-only display, acceptable).

## TASK-038a — Fix Module Status Dot Colors & Alert Banner False Positive
Date: 2026-03-15
Status: Complete
Summary: Fixed two cosmetic/UX issues on the live production site. Fix 1: module status dot colors in PipelineStatus.tsx now correctly map "running"/"ok"/"healthy" to green, "degraded"/"unknown"/"warning" to yellow, and all others (error/stopped) to red — previously "running" fell through to red despite green text pills. Fix 2: alert engine `_evaluate_absence` now checks US market hours (Mon-Fri 9:30-16:00 ET via `_is_us_market_hours()`) and subscribed symbol count before firing WebSocket disconnect alerts — resolves the BF-6 deferred item from TASK-038.
Files created: 0
Files modified: 2
Notes: Passed validation on first attempt. One minor issue: `_is_us_market_hours()` does not account for US market holidays (Christmas, Thanksgiving, etc.) — could fire false alerts on holidays. Bare `except Exception: pass` on WebSocket health check is acceptable (falls through to normal evaluation).

## TASK-039 — Complete Audit Event Emissions
Date: 2026-03-15
Status: Complete
Summary: Added 35+ audit event emissions across 15 backend files, completing the observability event catalog. Strategy module: 5 evaluation events (completed, skipped×2, error, auto_paused) in runner.py + 6 lifecycle events (enabled, disabled, paused, resumed, config_changed) in service.py + 1 safety monitor exit. Risk module: kill switch activated/deactivated with actor/reason/scope, 3 drawdown threshold events (warning/breach/catastrophic), daily loss breach, config changed. Paper trading: order.created + 6 distinct order.rejected points, 3 forex pool events (allocated/released/blocked), 2 shadow tracking events (fill_created/position_closed). Portfolio: 4 position lifecycle events (opened/scaled_in/scaled_out/closed with realized PnL), dividend.paid, split.adjusted, option.expired. Signals: deduplicated at debug severity. All emissions follow TASK-034 pattern (try/except wrapping, post-action timing, emoji prefixes, entity linkage).
Files created: 0
Files modified: 15
Notes: Passed validation on first attempt. Three minor items: (1) drawdown/daily_loss events lack entity_id (system-wide metrics with no natural entity — entity_id is optional in API), (2) drawdown events fire every check cycle not just on transitions (could be noisy), (3) daily_loss.breach is currently a no-op since daily loss calculation returns zero. Two deferred items: portfolio.cash.adjusted (no central cash manager exists) and drawdown transition detection.

## TASK-040 — Backtest Engine (Backend)
Date: 2026-03-15
Status: Complete
Summary: Built complete backtest engine as new `backtesting` module. Core bar replay runner walks historical OHLCV bars chronologically through existing ConditionEngine and indicator library (no reimplementation). 4 exit types: stop loss, take profit, signal-based (opposite direction closes), time-based (max_hold_bars). 4 position sizing types: fixed units, fixed cash, percent equity, percent risk (with JPY pip handling). Fill simulation with 0.5 pip slippage and 2 bps spread fees. 27 performance metrics including Sharpe ratio, max drawdown, profit factor, win/loss streaks, MFE/MAE. Equity curve sampled every 10 bars for 1m, every bar for higher timeframes, plus on trade events. 5 REST endpoints: POST trigger, GET run details, GET trades (paginated), GET equity curve (downsampled), GET list per strategy. All endpoints authenticated with strategy ownership verification. Strategy config frozen at backtest time for reproducibility. Failed backtests store error message. All financial math uses Decimal. Alembic migration creates 3 tables with CASCADE FKs and composite indexes.
Files created: 10
Files modified: 1
Notes: Passed validation on first attempt. Two minor items: (1) `symbols` type annotation in models.py says `dict` but should be `list` (runtime works fine since JSONB accepts both), (2) linear window growth `bar_dicts[:bar_index+1]` could be slow for 500K+ bar backtests (V1 trade-off). Synchronous execution may risk HTTP timeout for very large backtests.

## TASK-041 — Backtest UI (Frontend)
Date: 2026-03-15
Status: Complete
Summary: Built complete backtest frontend UI with 7 new files in `features/backtesting/`. BacktestForm on strategy detail page with full config (symbols, timeframe, date range, capital, 4 position sizing types, exit config with SL/TP/signal/max-hold), loading state with elapsed timer, 5-minute timeout. BacktestResultsList with 9-column DataTable (date, timeframe, period, trades, PnL, win rate, Sharpe, max DD, status). BacktestDetail view with header, 6 metric cards (Net PnL, Win Rate, Profit Factor, Sharpe, Max Drawdown, Total Trades), equity curve ComposedChart (equity line + drawdown area + initial capital reference line), and paginated/sortable trade table with exit reason badges and summary row. Route `/backtests/:id` added. Strategy detail page gains Backtest and Results tabs.
Files created: 7
Files modified: 2
Notes: Required re-validation after initial review found 3 issues (trade table not rendered, columns not sortable, no summary row). All 3 fixed and verified. Minor items: equity curve uses sample=300 instead of 200 (acceptable), symbol input uses comma-separated text instead of multi-select (documented), exit reason key mapping should be verified at runtime against backend values.

## TASK-041a — Fix Strategy Validation Symbols Format
Date: 2026-03-15
Status: Complete
Summary: Fixed 500 error when saving a strategy where `config.symbols` is a plain list (`["EUR_USD"]`) instead of a dict (`{"mode": "specific", "symbols": ["EUR_USD"]}`). Added `isinstance(symbols, list)` guards in `validation.py` (`_validate_completeness` and `_validate_symbols`) and `runner.py` (`_resolve_symbols`). List format treated as implicit "specific" mode. Dict format paths completely unchanged for backward compatibility.
Files created: 0
Files modified: 2
Notes: Passed validation on first attempt. Conservative fix — early returns for list format, no changes to existing dict logic.

## TASK-041b — Fix Strategy Config CamelCase/Snake_Case Mismatch
Date: 2026-03-15
Status: Complete
Summary: Fixed 400 error when saving strategies — frontend sends camelCase config keys (`entryConditions`, `exitConditions`, `positionSizing`, `riskManagement`) but backend validator expects snake_case. Added `normalize_config_keys()` function in validation.py with compiled regex, recursive key conversion. Applied at 4 entry points: `validation.validate()`, `runner.evaluate_strategy()`, `safety_monitor.run_check()`, and `backtesting.runner.run()`. Pure, stateless, idempotent — snake_case keys pass through unchanged.
Files created: 0
Files modified: 4
Notes: Passed validation on first attempt. Normalizer recursively converts all nested dict keys (handles nested camelCase like stopLoss.type). List items left unchanged.

## TASK-041c — Fix Strategy Detail Page Crash (profitFactor null guard)
Date: 2026-03-15
Status: Complete
Summary: Fixed crash on strategy detail page when metrics contain null or Infinity values. Added null guards (`!= null`, `?? 0`) and `isFinite()` checks on all `.toFixed()` calls in StrategyDetail.tsx (profitFactor, totalTrades, riskReward, sharpeRatio, avgHoldBars, maxDrawdown) and BacktestResultsList.tsx (sharpe ratio). When metrics are null/undefined, stat cards show `'—'` dash. Infinity profit factor displays `∞` symbol.
Files created: 0
Files modified: 2
Notes: Passed validation on first attempt. Minor note: sharpeRatio null check doesn't explicitly guard against Infinity, but backend returns null rather than Infinity for zero-std edge case.

## TASK-041d — Fix Strategy Save Payload & Exit Validation
Date: 2026-03-16
Status: Complete
Summary: Fixed two issues preventing strategy creation/editing. Fix 1: frontend update path (`PUT /strategies/{id}/config`) now wraps config under `{ config: {...} }` to match `UpdateStrategyConfigRequest` schema — create path was already correct. Fix 2: exit validation in `_validate_completeness` now checks `risk_management.stop_loss` and `risk_management.take_profit` as valid exit mechanisms in addition to `exit_conditions`. Runner's `_evaluate_exit` also falls back to `risk_management.*` for SL/TP/trailing stop lookups. Top-level keys take precedence via `or` fallback pattern.
Files created: 0
Files modified: 3
Notes: Passed validation on first attempt. Follow-up needed: `safety_monitor.py` still only checks top-level `stop_loss`/`take_profit`/`trailing_stop` config keys — does not check `risk_management.*` fallback. If SL/TP stored only under `risk_management`, safety monitor won't find them for orphaned positions.

## TASK-042 — Backtest & Strategy Builder Bug Fixes
Date: 2026-03-17
Status: Complete
Summary: Fixed 8 bugs across the strategy builder, backtest engine, and frontend. BF-1: Right-side indicator in condition builder now renders full parameter inputs (period, source, output selector). BF-2: Fixed sizing type strings to match backend (fixed, fixed_cash, percent_equity, percent_risk). BF-3: Strategy disable/pause/enable mutations send `{}` body to avoid 422. BF-4: Added delete button for draft strategies with confirmation dialog. BF-5: Null guards on config tab (`strategy.config ?? {}`, `v.changes ?? []`). BF-6: Backtest form pre-fills timeframe, symbols, SL/TP, max hold bars from strategy config. BF-7: Already fixed (Decimal→float in prior task). BF-8: Equity curve for 0-trade backtests shows flat line with backend fallback equity point and frontend Y-axis padding.
Files created: 0
Files modified: 5
Notes: BF-4 uses hard delete instead of soft delete suggested in task — acceptable since only draft strategies can be deleted (no signals, fills, or positions). BF-6 pre-fill uses `useRef` guard to run once and avoid overwriting user edits.

## TASK-043 — Strategy SDK + Python Strategy Runner
Date: 2026-03-17
Status: Complete
Summary: Built a complete Python strategy SDK enabling code-based strategies alongside the existing config-driven system. New `strategy_sdk` module with Strategy base class (lifecycle hooks: on_bar, on_start, on_stop, on_fill), StrategySignal dataclass, pandas-based indicator helpers (SMA, EMA, RSI, ATR, Bollinger, MACD, highest, lowest, crosses_above/below), TimeUtils (ET timezone), PipUtils (JPY handling), auto-discovery registry, runner with signal pipeline integration, and 5 REST API endpoints. Example SMA Crossover strategy in `strategies/` folder. Backend discovers strategies on startup.
Files created: 11
Files modified: 2
Notes: Market data stream hookup (calling runner.on_new_bar from bar processing pipeline) is deferred. Portfolio service stubs return defaults until wired. Strategy state is in-memory only (resets on restart). Uses zoneinfo (Python 3.12 stdlib) instead of pytz. Session factory pattern for signal creation matches existing alert engine pattern. Validator required one round of fixes for indicators API mismatch (DataFrame+source param) — resolved before PASS.

## TASK-044 — Backtest Engine Integration for Python Strategies
Date: 2026-03-17
Status: Complete
Summary: Extended the backtest engine to execute Python-based strategies alongside condition-based ones. New PythonBacktestRunner calls strategy lifecycle hooks (on_start/on_bar/on_stop), provides growing history DataFrame, per-signal SL/TP exit logic, state sync (positions/equity/cash), and parameter overrides. CLI tool for running backtests from command line (store_results=False to skip DB). Migration adds strategy_type and strategy_file columns to backtest_runs (strategy_id now nullable for Python strategies). Results stored in same tables, same metrics computation.
Files created: 3
Files modified: 5
Notes: O(n²) DataFrame construction per bar acknowledged — acceptable for V1. CLI uses store_results=False to avoid FK constraint violations (no BacktestRun in DB). Existing detail endpoints return 404 for Python backtests due to NULL strategy_id ownership check — needs follow-up. Validator required one round of fixes for CLI crash on backtests with trades.

## TASK-045 — London/NY Breakout Strategy
Date: 2026-03-17
Status: Complete
Summary: Implemented the London/NY Breakout strategy using the Python Strategy SDK — the first real strategy built on the new framework. Detects London session range (3-4 AM ET), validates range size (15-50 pips), and enters on breakout during NY overlap (8 AM-12 PM ET) with momentum confirmation (60%+ candle body, correct direction). Dynamic SL/TP from range bounds with configurable risk:reward ratio (default 1.5:1). Quality scoring system (0-100) across 5 weighted factors. One-trade-per-day limit. GBP_USD variant as a subclass. 11 configurable parameters exposed via get_parameters().
Files created: 1
Files modified: 0
Notes: Strategy works best with 5m bars (12 bars per range hour). With 1h bars, range window contains only 1 bar — less accurate range detection. Volume scoring gives default 15% credit since OANDA forex bars lack tick volume. float() conversions used throughout to handle both Decimal and float inputs from backtest runner.
