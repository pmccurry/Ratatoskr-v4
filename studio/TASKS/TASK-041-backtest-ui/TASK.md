# TASK-041 — Backtest UI (Frontend)

## Goal

Build the frontend interface for triggering backtests and viewing results. After this task, users can configure and launch a backtest from the strategy detail page, then view equity curves, trade lists, and performance metrics in a dedicated results view.

## Depends On

TASK-040 (backtest engine backend)

## Scope

**In scope:**
- Backtest trigger form on strategy detail page
- Backtest results list (per strategy)
- Backtest detail view with performance metrics
- Equity curve chart (line chart with drawdown overlay)
- Trade list table with pagination
- Loading state during backtest execution (30-120 seconds)

**Out of scope:**
- Backend changes (TASK-040 handles API)
- Walk-forward optimization UI
- Strategy optimization/parameter sweep
- Comparison of multiple backtests side-by-side (future feature)

---

## Views

### V1 — Backtest Trigger (on Strategy Detail page)

Add a "Backtest" tab or section to the existing strategy detail page. Contains a form:

**Configuration form:**
- **Symbols** — Multi-select from watchlist (default: all forex pairs for forex strategy, or specific equity symbols)
- **Timeframe** — Select: 1m, 1h, 4h, 1d (default: strategy's configured timeframe)
- **Date range** — Start date + end date pickers (default: last 90 days)
- **Initial capital** — Number input (default: $100,000)
- **Position sizing** — Select type + amount:
  - Fixed units: amount input
  - Fixed cash: amount input
  - % of equity: percent input
  - % risk: percent input + stop pips input
- **Exit configuration:**
  - Stop loss (pips): optional number input
  - Take profit (pips): optional number input
  - Signal exit: toggle (default: on)
  - Max hold bars: optional number input

**"Run Backtest" button** — triggers `POST /strategies/{id}/backtest`. Shows a loading spinner/progress bar during execution. On completion, navigates to the results view.

### V2 — Backtest Results List

Accessible from strategy detail page. Shows all past backtests for this strategy:

| Column | Content |
|--------|---------|
| Date | When the backtest was run |
| Timeframe | 1h, 4h, etc. |
| Period | Start — End date range |
| Trades | Total trade count |
| Net PnL | Total net PnL with color |
| Win Rate | Percentage |
| Sharpe | Ratio |
| Max DD | Max drawdown % |
| Status | Completed / Failed |

Clicking a row navigates to the detail view.

### V3 — Backtest Detail View

Full results for a single backtest run. Route: `/backtests/{id}`

**Header section:**
- Strategy name + backtest date
- Status badge (completed / failed)
- Duration (how long the backtest took to run)
- Configuration summary (symbols, timeframe, date range, sizing)

**Metrics cards (top row, similar to dashboard):**
| Card | Value |
|------|-------|
| Net PnL | Dollar amount + percent return (green/red) |
| Win Rate | Percentage with win/loss count |
| Profit Factor | Ratio |
| Sharpe Ratio | Annualized |
| Max Drawdown | Percentage |
| Total Trades | Count |

**Equity Curve chart (main section):**
- Line chart showing equity over time
- X-axis: date/time
- Y-axis: equity value
- Overlay: drawdown % (filled area below zero line, separate y-axis)
- Horizontal dashed line at initial capital for reference
- Use Recharts (already available in the project)

**Trade list table (below chart):**
| Column | Content |
|--------|---------|
| Symbol | Pair name |
| Side | Long/Short with color |
| Entry Time | Timestamp |
| Entry Price | Price |
| Exit Time | Timestamp |
| Exit Price | Price |
| PnL | Dollar amount (green/red) |
| PnL % | Percentage |
| Duration | Bars held |
| Exit Reason | SL/TP/Signal/Time/EOD |

Sortable by any column. Paginated (50 per page). Summary row at bottom with totals.

---

## Component Structure

```
frontend/src/features/backtesting/
├── BacktestForm.tsx           # V1 — trigger form
├── BacktestResultsList.tsx    # V2 — list of backtests per strategy
├── BacktestDetail.tsx         # V3 — full results view
├── BacktestMetricsCards.tsx   # Metric card row
├── EquityCurveChart.tsx       # Recharts line chart
├── BacktestTradeTable.tsx     # Trade list with pagination
└── backtestApi.ts             # API calls
```

---

## API Integration

```typescript
// backtestApi.ts
const api = axios.create({ baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1' });

export const runBacktest = (strategyId: string, params: BacktestParams) =>
  api.post(`/strategies/${strategyId}/backtest`, params);

export const getBacktest = (backtestId: string) =>
  api.get(`/backtests/${backtestId}`);

export const getBacktestTrades = (backtestId: string, page = 1, limit = 50) =>
  api.get(`/backtests/${backtestId}/trades`, { params: { page, limit } });

export const getBacktestEquityCurve = (backtestId: string, sample = 200) =>
  api.get(`/backtests/${backtestId}/equity-curve`, { params: { sample } });

export const getStrategyBacktests = (strategyId: string) =>
  api.get(`/strategies/${strategyId}/backtests`);
```

---

## Equity Curve Chart

Using Recharts (already in the project):

```tsx
<ResponsiveContainer width="100%" height={400}>
  <ComposedChart data={equityCurve}>
    <CartesianGrid strokeDasharray="3 3" />
    <XAxis dataKey="barTime" tickFormatter={formatDate} />
    <YAxis yAxisId="equity" domain={['auto', 'auto']} />
    <YAxis yAxisId="drawdown" orientation="right" domain={[0, 'auto']} />
    
    {/* Initial capital reference line */}
    <ReferenceLine yAxisId="equity" y={initialCapital} stroke="gray" strokeDasharray="4 4" />
    
    {/* Drawdown area (inverted, below zero) */}
    <Area yAxisId="drawdown" dataKey="drawdownPct" fill="rgba(255,80,80,0.15)" stroke="rgba(255,80,80,0.4)" />
    
    {/* Equity line */}
    <Line yAxisId="equity" dataKey="equity" stroke="#6366f1" dot={false} strokeWidth={2} />
    
    <Tooltip content={<CustomTooltip />} />
    <Legend />
  </ComposedChart>
</ResponsiveContainer>
```

---

## Loading State

Since backtests are synchronous (30-120 seconds), show a clear loading state:

```tsx
const [isRunning, setIsRunning] = useState(false);
const [elapsed, setElapsed] = useState(0);

// Timer during execution
useEffect(() => {
  if (!isRunning) return;
  const interval = setInterval(() => setElapsed(e => e + 1), 1000);
  return () => clearInterval(interval);
}, [isRunning]);

// UI
{isRunning && (
  <div className="backtest-loading">
    <Spinner />
    <p>Running backtest... {elapsed}s</p>
    <p className="text-secondary">Processing {params.symbols.length} pairs on {params.timeframe} timeframe</p>
  </div>
)}
```

---

## Routing

Add routes:
```tsx
<Route path="/backtests/:id" element={<BacktestDetail />} />
```

The backtest form and results list are part of the strategy detail page (new tab).

---

## Acceptance Criteria

| # | Criterion |
|---|-----------|
| AC1 | Backtest form renders on strategy detail page with all configuration fields |
| AC2 | Symbol multi-select shows available pairs from watchlist |
| AC3 | Position sizing section changes inputs based on selected type |
| AC4 | Exit config section has SL/TP/signal-exit/max-hold inputs |
| AC5 | "Run Backtest" button triggers API call and shows loading state with elapsed timer |
| AC6 | On completion, navigates to backtest detail view |
| AC7 | On failure, shows error message from API response |
| AC8 | Backtest results list shows all backtests for the strategy with key metrics |
| AC9 | Clicking a result row navigates to detail view |
| AC10 | Detail view shows 6 metric cards (PnL, win rate, profit factor, Sharpe, drawdown, trades) |
| AC11 | Equity curve renders as line chart with drawdown overlay |
| AC12 | Initial capital shown as reference line on equity chart |
| AC13 | Trade table shows all trades with pagination (50/page) |
| AC14 | Trade table sortable by PnL, duration, or any column |
| AC15 | PnL values colored green (positive) / red (negative) |
| AC16 | Exit reason shown for each trade (SL, TP, Signal, Time, EOD) |
| AC17 | Route `/backtests/:id` works |
| AC18 | No backend code modified |
| AC19 | Nothing inside /studio modified (except BUILDER_OUTPUT.md) |

---

## Files to Create

| File | Purpose |
|------|---------|
| `frontend/src/features/backtesting/BacktestForm.tsx` | Trigger form with config |
| `frontend/src/features/backtesting/BacktestResultsList.tsx` | Past backtests table |
| `frontend/src/features/backtesting/BacktestDetail.tsx` | Full results page |
| `frontend/src/features/backtesting/BacktestMetricsCards.tsx` | Metric card row |
| `frontend/src/features/backtesting/EquityCurveChart.tsx` | Recharts equity + drawdown |
| `frontend/src/features/backtesting/BacktestTradeTable.tsx` | Trade list + pagination |
| `frontend/src/features/backtesting/backtestApi.ts` | API calls |

## Files to Modify

| File | What Changes |
|------|-------------|
| `frontend/src/app/router.tsx` | Add `/backtests/:id` route |
| `frontend/src/pages/StrategyDetail.tsx` | Add Backtest tab with form + results list |

## Files NOT to Touch

- Backend code
- Studio files
- Test files

---

## Builder Notes

- **Follow the existing design system.** Match the dark theme, card styles, table patterns, and color palette already used in the dashboard, portfolio, and system pages.
- **Recharts is already available.** Import from `recharts` — it's in the project dependencies. Use `ComposedChart` for the equity + drawdown overlay.
- **The backtest API is synchronous.** The POST request blocks for 30-120 seconds. Use a generous timeout on the axios call (`timeout: 300000` — 5 minutes) and show the elapsed timer so the user knows it's working.
- **Number formatting.** Use the existing `formatPnl`, `formatPercent`, `formatCurrency` utilities from the project. Don't create new formatters.
- **The form should have sensible defaults.** Pre-fill: last 90 days, $100K capital, fixed 10000 units, signal exit enabled, no SL/TP (user adds if wanted).
- **Equity curve downsampling.** For 1m backtests over 30 days, the equity curve could have thousands of points. Use `?sample=200` to get a manageable number for charting.

## References

- frontend_specs.md — component structure, styling, routing patterns
- TASK-040 — API endpoint shapes and response formats
