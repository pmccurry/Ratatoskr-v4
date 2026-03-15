# DECISIONS

## DECISION-001
Title: Use modular monolith architecture for MVP
Status: Approved
Reason: Faster iteration, simpler deployment, lower coordination overhead, easier early refactoring
Impact:
- backend structure
- deployment design
- repo organization
- task scoping
Date: 2026-03-10

---

## DECISION-002
Title: Research and paper trading before live trading
Status: Approved
Reason: Safer product development, clearer validation path, lower implementation risk
Impact:
- roadmap
- execution layer
- risk layer
- task prioritization
Date: 2026-03-10

---

## DECISION-003
Title: Desktop-first workflow priority
Status: Approved
Reason: Quant/algo users need dense, high-signal operator workflows better suited to desktop layouts
Impact:
- frontend architecture
- dashboard structure
- component layout
- strategy builder is desktop-only
Date: 2026-03-10

---

## DECISION-004
Title: Use persistent studio files as project memory
Status: Approved
Reason: Prevent agent drift and avoid relying on loose chat memory
Impact:
- all agent prompts
- coding workflow
- validation workflow
Date: 2026-03-10

---

## DECISION-005
Title: All build work must flow through scoped task packets
Status: Approved
Reason: Prevent uncontrolled code generation and keep Codex / Claude Code aligned to current scope
Impact:
- coding agent workflow
- supervisor workflow
- validator workflow
Date: 2026-03-10

---

## DECISION-006
Title: Product aesthetic is dark, calm, operator-focused SaaS
Status: Approved
Reason: Align the platform with professional trading workflows instead of retail brokerage aesthetics
Impact:
- UI architecture
- frontend prompts
- component design
- dark theme only for MVP
Date: 2026-03-10

---

## DECISION-007
Title: Backend stack is Python 3.12 + FastAPI
Status: Approved
Reason: Best fit for quant workflows, strong Python ecosystem, modern async API support
Impact:
- backend scaffolding
- API architecture
- dependency management
- service/module conventions
Date: 2026-03-10

---

## DECISION-008
Title: Frontend stack is React + Vite + TypeScript
Status: Approved
Reason: Strong dashboard ecosystem, fast local development, clean fit for operator-focused SPA workflows
Impact:
- frontend scaffolding
- routing
- component architecture
- client build pipeline
Date: 2026-03-10

---

## DECISION-009
Title: Database is PostgreSQL for MVP
Status: Approved
Reason: Strong production-ready foundation for structured persistence and future growth
Impact:
- persistence layer
- migration tooling
- local dev setup
- infra config
Date: 2026-03-10

---

## DECISION-010
Title: Python project manager is uv
Status: Approved
Reason: Fast unified tooling for Python versioning, dependency management, and environment setup
Impact:
- environment setup
- dependency install workflow
- onboarding docs
Date: 2026-03-10

---

## DECISION-011
Title: API is REST-first for MVP
Status: Approved
Reason: Simpler implementation and validation path for early milestones; WebSockets can be added later for streaming views
Impact:
- backend API design
- frontend data access patterns
- task scoping
Date: 2026-03-10

---

## DECISION-012
Title: WebSocket streaming for real-time market data ingestion
Status: Approved
Reason: Both Alpaca and OANDA support WebSocket bar streaming. Eliminates REST polling for data ingestion, avoids rate limit concerns, provides near-real-time data flow. REST API budget preserved for universe filter, backfill, order placement, and account queries.
Impact:
- market data module architecture
- WebSocket manager component
- async bar processing pipeline
- connection lifecycle management
Date: 2026-03-12

---

## DECISION-013
Title: Store 1m bars from stream, aggregate higher timeframes on write
Status: Approved
Reason: Single source resolution (1m) from the stream. Higher timeframes (5m, 15m, 1h, 4h, 1d) are aggregated immediately when a complete window of 1m bars exists. Avoids redundant API calls for multiple timeframes. All aggregation from 1m directly (not cascading) to prevent compounding errors.
Impact:
- bar storage pipeline
- aggregation engine
- strategy read path
- backfill strategy (1m fetched, higher timeframes fetched directly for long history)
Date: 2026-03-12

---

## DECISION-014
Title: Option chain data fetched on demand, not streamed
Status: Approved
Reason: Options data volume is orders of magnitude larger than equity bars (thousands of contracts per underlying). Streaming all chains is impractical. On-demand fetch with short-lived in-memory cache (60s TTL) serves strategy evaluation, position management, and execution needs efficiently.
Impact:
- market data module (options sub-module)
- strategy evaluation for options strategies
- API rate budget (option chain = 1 REST call per underlying)
Date: 2026-03-12

---

## DECISION-015
Title: Config-driven strategies as the primary path (no code required)
Status: Approved
Reason: Users should be able to build strategies through the UI by selecting indicators, setting conditions, and configuring parameters. Covers 80-90% of strategies. Three tiers: (1) indicator condition builder, (2) custom formula expressions, (3) sandboxed code editor (deferred). Class-based custom strategies are the escape hatch, not the primary path.
Impact:
- strategy module architecture (indicator catalog, condition engine, formula parser)
- strategy builder UI (the most complex frontend view)
- strategy runner (evaluates config, not code)
- user accessibility (layman-friendly)
Date: 2026-03-12

---

## DECISION-016
Title: Forex account pool model for US FIFO netting compliance
Status: Approved
Reason: US forex brokers enforce FIFO netting — one net direction per pair per account. Multiple strategies trading the same pair require separate accounts. The system maintains a pool of virtual accounts (paper) or real OANDA accounts (live). Each account can hold multiple pairs but only one position per pair. Allocation is per-pair, not per-account.
Impact:
- paper trading module (forex pool manager, allocation logic)
- risk engine (account availability check for forex signals)
- portfolio module (per-account cash and position tracking for forex)
- live trading preparation (virtual accounts map to real OANDA accounts)
Date: 2026-03-12

---

## DECISION-017
Title: Shadow tracking for contention-blocked forex signals
Status: Approved
Reason: When a forex signal is blocked due to account pool contention (all accounts occupied for that pair), the system records what would have happened via shadow fills and shadow positions. This enables fair strategy comparison without contention bias. Shadow tracking is completely isolated from real tracking.
Impact:
- paper trading module (shadow tracker, shadow position evaluator)
- strategy comparison analytics
- portfolio views (real vs true performance display)
- only activates for reason_code "no_available_account", forex only
Date: 2026-03-12

---

## DECISION-018
Title: Broker paper trading for equities, internal simulation for forex
Status: Approved
Reason: Alpaca paper trading API provides realistic fill simulation against live market data for equities. Forex uses internal simulation because the account pool model requires coordinated virtual account management that doesn't map to a single broker practice account. Executor abstraction supports both modes behind the same interface.
Impact:
- paper trading module (executor abstraction with multiple implementations)
- fill realism (equities: broker-quality, forex: configurable slippage/fees)
- transition to live (equities: swap API URL, forex: map virtual accounts to real)
Date: 2026-03-12

---

## DECISION-019
Title: Safety monitor for orphaned positions
Status: Approved
Reason: When a strategy is paused, disabled, or auto-paused due to errors, open positions must still have automated exit protection. The safety monitor evaluates stop loss, take profit, and trailing stop for orphaned positions on a 1m cycle regardless of the strategy's original timeframe. Positions always have something watching them.
Impact:
- strategy module (safety monitor component)
- position protection guarantee
- auto-pause workflow (positions transfer to safety monitor)
- alert system (notify user of orphaned positions)
Date: 2026-03-12

---

## DECISION-020
Title: Strategies can be edited while enabled (live editing with versioning)
Status: Approved
Reason: Requiring disable/re-enable to tweak parameters is bad UX and raises questions about open positions. Exit rule changes apply to existing positions on next evaluation. Entry rule changes affect future only. Symbol removal with open positions prompts user for explicit choice. All changes create a new config version for audit trail.
Impact:
- strategy module (version management, edit-while-enabled logic)
- position management (exit rules update on existing positions)
- frontend (diff view before saving changes)
Date: 2026-03-12

---

## DECISION-021
Title: Manual position close always flows through the pipeline
Status: Approved
Reason: Manual closes create a signal (source="manual") that goes through risk evaluation (light check) and paper trading (fill simulation). This ensures all closes are logged, audited, and reflected in portfolio accounting consistently. Re-entry cooldown prevents strategies from immediately re-entering after manual close.
Impact:
- signal module (source field: strategy | manual | safety | system)
- risk module (lighter evaluation for exit signals)
- paper trading module (processes manual close fills)
- portfolio module (consistent accounting)
Date: 2026-03-12

---

## DECISION-022
Title: Kill switch blocks entries but always allows exits
Status: Approved
Reason: The emergency stop should prevent new risk, not trap existing risk. When the kill switch is active, all entry signals are rejected but all exit signals are approved. This allows the system (and user) to reduce exposure while preventing new positions.
Impact:
- risk module (kill switch check behavior)
- safety monitor (continues to function under kill switch)
- manual closes (always honored)
Date: 2026-03-12

---

## DECISION-023
Title: Dividend and corporate action processing in portfolio module
Status: Approved
Reason: Dividends affect PnL tracking, cash balances, and strategy performance metrics. Without tracking, positions show incorrect losses on ex-dates. The system fetches corporate actions from Alpaca daily (30-day lookforward), processes dividends on ex-date (eligibility) and payable date (cash credit), and adjusts positions for stock splits. Dividend income is tracked separately from price PnL (no cost basis adjustment).
Impact:
- market data module (dividend announcement fetching and storage)
- portfolio module (dividend payment processing, split adjustment)
- strategy module (dividend indicators: yield, days_to_ex_date, amount)
- dashboard (dividend income views, total return including dividends)
Date: 2026-03-12

---

## DECISION-024
Title: Emoji-prefixed event summaries for activity feed
Status: Approved
Reason: The activity feed is the primary real-time view of system activity. Emoji prefixes enable at-a-glance scanning without reading full text. Each event category has a standard emoji (📊 strategy, ✅ approved, ❌ rejected, 💰 fills, 📂 positions, 🛑 kill switch, etc.).
Impact:
- observability module (event summary format convention)
- frontend activity feed component
- all modules that emit events
Date: 2026-03-12
