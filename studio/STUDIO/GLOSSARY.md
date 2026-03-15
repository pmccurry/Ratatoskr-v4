# GLOSSARY

## Strategy
A defined trading logic unit that evaluates market data and can generate signals. In this system, strategies are primarily config-driven (indicator conditions, formulas) rather than code-based.

## Strategy Version
A versioned snapshot of a strategy's configuration. Created automatically when an enabled strategy's config is modified. Every signal references the strategy version that produced it.

## Strategy Config
The full structured definition of a strategy: entry conditions, exit conditions, risk management rules, position sizing, symbol selection, and schedule. Stored as JSON in the strategy_configs table.

## Indicator
A technical analysis function that computes a value from bar data (e.g., RSI, EMA, MACD). Registered in the indicator catalog with defined parameters, outputs, and valid ranges.

## Condition
A comparison between an indicator value (or formula) and a target value or another indicator. Combined into condition groups with AND/OR logic to form entry and exit rules.

## Condition Engine
The runtime component that evaluates condition groups against computed indicator values. Returns true/false for a given set of conditions against current bar data.

## Formula Expression
A custom mathematical expression using indicator functions and bar values (e.g., "(close - ema(close, 200)) / atr(14)"). Parsed and evaluated safely without allowing arbitrary code execution.

## Signal
A strategy-generated intent indicating a possible action such as buy, sell, enter, or exit. Signals are persisted, validated, deduplicated, and evaluated by the risk engine before becoming orders.

## Signal Source
The origin of a signal: "strategy" (from evaluation), "manual" (user-initiated close), "safety" (safety monitor exit), or "system" (kill switch / auto-close).

## Order
A structured instruction submitted to the paper trading engine representing an intended execution action. Created from risk-approved signals.

## Fill
A simulated execution result for an order. Records the execution price (after slippage), fees, and reference price. Triggers portfolio position updates.

## Shadow Fill
A simulated fill for a forex signal that was blocked due to account pool contention. Tracks what would have happened for fair strategy comparison. Completely isolated from real fills.

## Shadow Position
A position created from shadow fills. Fully managed (exit conditions evaluated, PnL tracked) but never affects real portfolio state.

## Trade
A completed execution event: the combination of an entry fill and an exit fill for the same position.

## Position
The current held quantity and basis information for a symbol within a strategy's portfolio. Tracks entry price, current price, unrealized PnL, dividends received, and exit rule levels.

## Position Override
A user-set override on a specific position's exit rules (stop loss, take profit, trailing stop) that takes precedence over the strategy's config for that position only.

## Realized PnL
Profit or loss locked in after closing all or part of a position. Recorded in the realized PnL ledger as an append-only entry.

## Unrealized PnL
Profit or loss based on current market value of open positions. Updated on every mark-to-market cycle.

## Total Return
The sum of unrealized PnL, realized PnL, and dividend income for a position or strategy. More accurate than price PnL alone for dividend-paying stocks.

## Equity
Total paper account value: cash balance plus marked-to-market value of all open positions.

## Peak Equity
The historical high-water mark of equity. Used for drawdown calculation. Never auto-resets; manual reset available for admin after adding capital.

## Drawdown
The decline from peak equity to current equity, expressed as a percentage. Three threshold levels: warning, breach, and catastrophic.

## Paper Trading
Simulated trading without real market execution. Uses broker paper APIs (Alpaca) or internal simulation (forex with account pool). Enforces the same constraints as live trading for honest results.

## Risk Gate
A rule or control that can approve, modify, or reject a proposed trading action. The risk engine applies 12 ordered checks to every signal.

## Risk Decision
The output of risk evaluation for a signal. Records the outcome (approved/rejected/modified), which checks passed, which check failed, and a snapshot of portfolio state at decision time.

## Kill Switch
An emergency control that blocks all new entry signals while allowing exits. Can be global (all strategies) or per-strategy. Persists across restarts.

## Safety Monitor
A lightweight process that monitors orphaned positions (strategy paused, disabled, or errored) by checking stop loss, take profit, and trailing stop on a 1-minute cycle. Ensures positions always have something watching them.

## Backtest Run
A specific execution of a strategy over historical data producing metrics and artifacts. Uses the same internal fill simulation as paper trading.

## Market Data
Normalized historical or current price and volume data used by strategies and system components. Sourced from Alpaca (equities/options) and OANDA (forex).

## OHLCV Bar
A single candle/bar of market data: open, high, low, close, volume for a specific symbol, timeframe, and timestamp.

## Watchlist
The curated set of symbols the system actively monitors. Produced by the universe filter (equities) or static config (forex). Only watchlist symbols receive streaming data.

## Universe Filter
A daily job that narrows the full set of available symbols to a tradable watchlist based on criteria (volume, price, exchange, etc.).

## Broker Adapter
An implementation of the common market data interface for a specific broker (Alpaca, OANDA). Handles broker-specific API calls, authentication, and data normalization.

## Executor
An implementation of the order execution interface. Modes: simulated (internal fill calculation), paper (broker paper API), live (broker live API, future).

## Forex Account Pool
A set of virtual (paper) or real (live) OANDA accounts used to manage FIFO netting constraints. Each account can hold one position per currency pair. Strategies are allocated accounts per-pair when they open positions.

## Account Allocation
The assignment of a forex account to a specific strategy for a specific currency pair. Released when the position closes, freeing the account for other strategies on that pair.

## Dividend Announcement
Market data about an upcoming or past dividend: declaration date, ex-date, record date, payable date, and cash amount per share.

## Ex-Dividend Date (Ex-Date)
The date on which a stock begins trading without the dividend. Holders before this date are eligible for the dividend payment.

## Mark-to-Market
The periodic process of updating all open positions with current market prices, recalculating unrealized PnL, market value, and tracking fields (highest/lowest price since entry).

## Portfolio Snapshot
A point-in-time record of portfolio state: equity, cash, positions value, PnL, drawdown. Taken periodically (every 5 minutes), on events (after fills), and at daily close.

## Audit Event
A structured business-level event record stored in the audit_events table. Every significant action across all modules produces an audit event with category, severity, summary, and details.

## Alert Rule
A condition definition that triggers notifications when met. Three types: event_match (specific event occurs), metric_threshold (metric exceeds value for duration), absence (expected event doesn't occur).

## Stat Card
A dashboard UI component displaying a single key metric (value, label, trend indicator). Used across dashboard home, strategy detail, risk dashboard.

## Activity Feed
A real-time stream of audit events displayed in the dashboard, with emoji prefixes for at-a-glance scanning. Filterable by category, severity, strategy, and symbol.
