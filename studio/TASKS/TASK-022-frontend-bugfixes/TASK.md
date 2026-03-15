# TASK-022 — Frontend Bug Fixes

## Task Status
- Builder:    [ ] not started
- Validator:  [ ] not started
- Librarian:  [ ] not started

## Objective

Fix all known frontend bugs identified during the build validation cycle.
These were flagged by Validators during TASK-015 through TASK-020.

After this task:
- All 16 frontend bugs are fixed (or explicitly deferred with comment)
- 3 unused components are either wired in or removed
- No backend changes
- No new views or major features

## Read First

1. /studio/SPECS/frontend_specs.md — theme colors, component conventions
2. This task file (the bug descriptions below ARE the spec)

## Constraints

- Fix ONLY the listed bugs — no new views, no new features
- Do NOT modify any backend code
- Do NOT create, modify, or delete anything inside /studio (except BUILDER_OUTPUT.md)
- Do NOT modify /CLAUDE.md
- Each fix should be the minimum change needed
- Tailwind utility classes only — the project uses `text-error` not `text-danger`

---

## Bug Fixes

### FIX-F1 (MAJOR): `text-danger` instead of `text-error` in 4 files

**Files:**
- frontend/src/features/orders/OrderTable.tsx
- frontend/src/features/orders/FillTable.tsx
- frontend/src/features/orders/ForexPoolStatus.tsx
- frontend/src/features/orders/ShadowComparison.tsx

**Problem:** These files use `text-danger` for sell-side / negative value
styling. The project's Tailwind config defines `text-error` (mapped to
#ef4444), not `text-danger`. The text renders with no color applied.

**Fix:** Find and replace all instances of `text-danger` with `text-error`
in these four files. Also search the entire frontend for any other
instances of `text-danger` that may exist elsewhere.

**Verify:** Sell-side text renders in red (#ef4444) on Orders, Fills,
Forex Pool, and Shadow Comparison views.

---

### FIX-F2 (MEDIUM): Math.random() for radio button names in ConditionRow

**File:** frontend/src/features/strategies/ConditionBuilder.tsx (or ConditionRow within it)

**Problem:** Radio button `name` attributes use `Math.random()` to
generate unique names. This causes React to generate new names on every
re-render, which makes radio buttons lose their grouping and flicker.

**Fix:** Replace `Math.random()` with a stable identifier. Use the
condition's index or a `useId()` hook (React 18+) to generate a stable
unique name per condition row.

```tsx
// BEFORE (broken):
<input type="radio" name={`right-type-${Math.random()}`} />

// AFTER (fixed):
const radioId = useId();
<input type="radio" name={`right-type-${radioId}`} />
```

**Verify:** Radio buttons in condition rows maintain their grouping
across re-renders. No flickering when typing in other fields.

---

### FIX-F3 (LOW): ActivityFeed "execution" category filter mismatch

**File:** frontend/src/features/dashboard/ActivityFeed.tsx

**Problem:** The category filter includes "execution" as an option, but
the backend uses category "paper_trading" for execution-related events.
Filtering by "execution" returns no results.

**Fix:** Either rename the filter option to "Trading" with value
"paper_trading", or map "execution" to "paper_trading" in the filter
query. The former is better UX since "Trading" matches the sidebar nav
label.

**Verify:** Filtering activity feed by the trading/execution category
returns paper trading events.

---

### FIX-F4 (LOW): Duplicate "Edit in Settings" links

**File:** frontend/src/pages/Risk.tsx and/or frontend/src/features/risk/RiskConfigSummary.tsx

**Problem:** The Risk page renders two "Edit in Settings" links — one
from the RiskConfigSummary component and one from the page layout.

**Fix:** Remove one of the duplicate links. Keep the one inside the
RiskConfigSummary component (it's contextually closer to the config
display).

**Verify:** Only one "Edit in Settings" link appears on the Risk page.

---

### FIX-F5 (MEDIUM): StrategyStatusList shows market+version instead of PnL+position count

**File:** frontend/src/features/dashboard/StrategyStatusList.tsx

**Problem:** The dashboard's strategy status list shows market and version
for each strategy, but the frontend spec says it should show
"PnL (total) | Win rate | Open positions count" per the strategy card
content spec.

**Fix:** Update the subtitle/detail line to show:
- Total PnL (from portfolio metrics if available, or "—" if no data)
- Position count (from portfolio positions count, or "0")

Since the strategy list endpoint may not include embedded PnL data,
this may need to show what's available from the strategy list response.
At minimum, replace market+version with status + last evaluated time,
which is more useful on a dashboard summary.

**Verify:** Strategy items in the dashboard status list show operationally
useful information (not just market/version which is static metadata).

---

### FIX-F6 (MEDIUM): EditStopLossDialog SL/TP fields not pre-filled

**File:** frontend/src/features/portfolio/EditStopLossDialog.tsx

**Problem:** When opening the edit SL/TP dialog for a position, the
input fields start empty instead of showing the current stop loss and
take profit values.

**Fix:** Pass the current SL/TP values as props to the dialog and use
them as `defaultValue` (for uncontrolled) or initial state (for controlled)
on the input fields.

```tsx
// The dialog should receive current values:
interface EditStopLossDialogProps {
  position: Position;
  currentStopLoss?: number;
  currentTakeProfit?: number;
  onSave: (sl: number, tp: number) => void;
  onClose: () => void;
}

// Initialize state from props:
const [stopLoss, setStopLoss] = useState(currentStopLoss?.toString() ?? '');
const [takeProfit, setTakeProfit] = useState(currentTakeProfit?.toString() ?? '');
```

**Verify:** Opening the SL/TP dialog shows the current values pre-filled.
Empty fields only appear when no SL/TP is currently set.

---

### FIX-F7 (MEDIUM): SignalTable pagination uses client-side total

**File:** frontend/src/features/signals/SignalTable.tsx

**Problem:** Pagination controls use `tableData.length` (the current page's
row count) as the total, instead of the server's `pagination.totalItems`.
This means "Showing 1-20 of 20" even when there are 200 total signals.

**Fix:** Use the `totalItems` from the API's paginated response for the
pagination display and page count calculation.

```tsx
// BEFORE:
const totalPages = Math.ceil(data.length / pageSize);

// AFTER:
const totalPages = Math.ceil(pagination.totalItems / pageSize);
```

**Verify:** Signal table pagination shows correct total count from
the server and allows navigating to all pages.

---

### FIX-F8 (MEDIUM): OrderTable missing pagination controls

**File:** frontend/src/features/orders/OrderTable.tsx

**Problem:** The order table renders data but has no pagination controls
at all. If there are more orders than one page, users can't see them.

**Fix:** Add pagination controls matching the pattern used in SignalTable
or DataTable. Include prev/next buttons, page number display, and
total count from the server response.

**Verify:** Order table has working pagination controls. Users can
navigate between pages of orders.

---

### FIX-F9 (LOW): Strategy filter is raw UUID text input

**Files:**
- frontend/src/features/signals/SignalTable.tsx (or parent filter bar)
- frontend/src/features/orders/OrderTable.tsx (or parent filter bar)

**Problem:** The strategy filter on Signals and Orders pages is a raw
text input where users must type a strategy UUID. Should be a dropdown
select populated from the user's strategies.

**Fix:** Replace the text input with a select dropdown. Fetch strategies
via `GET /strategies` and populate the options with strategy name + key.

```tsx
const { data: strategies } = useQuery({
  queryKey: ['strategies'],
  queryFn: () => api.get('/strategies'),
  staleTime: 60_000,
});

<select value={strategyFilter} onChange={...}>
  <option value="">All Strategies</option>
  {strategies?.data?.map(s => (
    <option key={s.id} value={s.id}>{s.name}</option>
  ))}
</select>
```

**Verify:** Strategy filter on Signals and Orders pages is a dropdown
showing strategy names, not a text input for UUIDs.

---

### FIX-F10 (LOW): Fill filter missing date range

**File:** frontend/src/features/orders/FillTable.tsx (or parent filter component)

**Problem:** The fills tab has a side filter but no date range filter.
The spec calls for date range filtering on fills.

**Fix:** Add date range inputs (start date, end date) to the fills
filter bar. Wire them into the API query params (`date_start`, `date_end`).

**Verify:** Fills tab has date range filter inputs that filter results
when dates are selected.

---

### FIX-F11 (LOW): EquityCurve missing YTD period

**File:** frontend/src/features/portfolio/EquityCurve.tsx

**Problem:** The period selector has 1d, 7d, 30d, 90d, All but is
missing YTD (year-to-date) which was specified in the frontend spec.

**Fix:** Add "YTD" option to the period selector. Calculate the start
date as January 1 of the current year.

```tsx
const periods = [
  { label: '1D', value: '1d' },
  { label: '7D', value: '7d' },
  { label: '30D', value: '30d' },
  { label: '90D', value: '90d' },
  { label: 'YTD', value: 'ytd' },
  { label: 'All', value: 'all' },
];

// When 'ytd' selected:
const start = new Date(new Date().getFullYear(), 0, 1).toISOString();
```

**Verify:** Equity curve period selector includes YTD option and
correctly filters chart data from January 1 of the current year.

---

### FIX-F12 (LOW): Win/loss distribution chart uses single color

**File:** frontend/src/features/portfolio/PnlSummary.tsx (or wherever the
win/loss distribution histogram is rendered)

**Problem:** The win/loss distribution chart uses a single accent color
for all bars. Winning buckets should be green, losing buckets should be red.

**Fix:** Use conditional bar colors based on the bucket value:
- Positive PnL buckets: success color (#22c55e)
- Negative PnL buckets: error color (#ef4444)

```tsx
// Recharts BarChart with conditional fill:
<Bar dataKey="count">
  {data.map((entry, index) => (
    <Cell key={index} fill={entry.bucket >= 0 ? '#22c55e' : '#ef4444'} />
  ))}
</Bar>
```

**Verify:** Win/loss distribution chart shows green bars for positive
PnL buckets and red bars for negative PnL buckets.

---

### FIX-F13 (LOW): ClosePositionDialog — single button instead of dropdown

**File:** frontend/src/features/portfolio/PositionTable.tsx (or wherever
the close action is rendered)

**Problem:** The close button is a single "Close" button. The spec calls
for a dropdown with "Close All" and "Close Partial" options.

**Fix:** Replace the single button with a dropdown menu using the
DropdownMenu component pattern. Two options:
- "Close All" — closes the full position quantity
- "Close Partial" — opens a dialog for entering partial quantity

For MVP, if "Close Partial" is complex, add it as a disabled option
with "(coming soon)" label and keep "Close All" functional.

**Verify:** Close action is a dropdown menu, not a single button.
At minimum "Close All" option works.

---

### FIX-F14 (LOW — DEFER): Risk config change history table

**File:** frontend/src/pages/Settings.tsx (Risk Config tab)

**Problem:** The change history table is not rendered because the
`GET /risk/config/audit` endpoint exists but the frontend doesn't
call it.

**Fix:** Add a TanStack Query call to `GET /risk/config/audit` and
render the results in a DataTable below the config form. Columns:
field, old value, new value, changed by, timestamp.

If the audit endpoint response format is unclear, render a basic
table with whatever the endpoint returns.

**Verify:** Risk Config tab in Settings shows a change history table
below the edit form.

---

### FIX-F15 (LOW — DEFER): Pipeline throughput sparkline mini-charts

**File:** frontend/src/features/system/ThroughputMetrics.tsx

**Problem:** The throughput metrics cards show numeric values but no
sparkline mini-charts as specified. Sparklines require time-series
metric data from `GET /observability/metrics/:name`.

**Fix:** If the metrics endpoint returns time-series data, render
small inline Recharts LineChart (sparkline style, no axes, no grid,
just the line) inside each metric card.

If the endpoint only returns current values (not time series), add
a comment noting this limitation and skip the sparklines. The numeric
values are sufficient for MVP.

**Verify:** Either sparkline charts render in throughput cards, or a
code comment explains why they're deferred (endpoint limitation).

---

### FIX-F16 (LOW — DEFER): Evaluation log expandable rows

**File:** frontend/src/features/strategies/StrategyDetail.tsx (Evaluation Log tab)

**Problem:** Evaluation log rows are not expandable to show per-symbol
evaluation detail. The DataTable component may not support expandable rows.

**Fix:** Add click-to-expand behavior on evaluation log rows. When
expanded, show the `details_json` from the evaluation record in a
formatted detail view.

If the DataTable component doesn't support expandable rows, use a
simple pattern: clicking a row opens a detail panel below it using
conditional rendering.

```tsx
const [expandedId, setExpandedId] = useState<string | null>(null);

{evaluations.map(eval => (
  <>
    <tr onClick={() => setExpandedId(expandedId === eval.id ? null : eval.id)}>
      {/* normal row cells */}
    </tr>
    {expandedId === eval.id && (
      <tr><td colSpan={7}>
        <pre>{JSON.stringify(eval.detailsJson, null, 2)}</pre>
      </td></tr>
    )}
  </>
))}
```

**Verify:** Clicking an evaluation log row expands it to show detail.

---

## Unused Component Cleanup

### U1: IndicatorSelect.tsx
**File:** frontend/src/features/strategies/IndicatorSelect.tsx
**Problem:** Created but ConditionBuilder renders its own inline indicator
select. This component is never imported.
**Fix:** Either wire it into the ConditionBuilder (replacing the inline
select), or delete it. If the inline version works correctly, delete
the unused file.

### U2: ClosePositionDialog.tsx
**File:** frontend/src/features/portfolio/ClosePositionDialog.tsx
**Problem:** Created but PositionTable uses its own inline ConfirmDialog.
Never imported.
**Fix:** If FIX-F13 (dropdown close) needs a partial-close dialog, wire
this component in. Otherwise delete it.

### U3: FormulaInput.tsx
**File:** frontend/src/features/strategies/FormulaInput.tsx
**Problem:** Created but ConditionBuilder uses inline formula text input.
Never imported.
**Fix:** Either wire it into the ConditionBuilder (replacing the inline
input with this richer component), or delete it. If the inline version
works, delete the unused file.

---

## Acceptance Criteria

### Styling Fixes
1. All instances of `text-danger` replaced with `text-error` across entire frontend
2. No other non-existent Tailwind classes used in modified files

### Functional Fixes
3. ConditionRow radio buttons use stable IDs (useId or index), not Math.random()
4. ActivityFeed category filter maps correctly to backend categories
5. Only one "Edit in Settings" link on Risk page
6. StrategyStatusList shows operationally useful data (not just market+version)
7. EditStopLossDialog pre-fills current SL/TP values
8. SignalTable pagination uses server totalItems (not client data.length)
9. OrderTable has working pagination controls
10. Strategy filter on Signals page is a dropdown, not UUID text input
11. Strategy filter on Orders page is a dropdown, not UUID text input
12. Fills tab has date range filter inputs
13. EquityCurve period selector includes YTD option
14. Win/loss distribution chart uses green (positive) and red (negative) bar colors
15. Close position action is a dropdown menu (Close All at minimum)

### Deferred Items (comment in code is acceptable)
16. Risk config change history table renders (or has TODO with endpoint call)
17. Sparkline mini-charts render (or have comment explaining deferral)
18. Evaluation log expandable rows work (or have basic expand pattern)

### Unused Components
19. IndicatorSelect.tsx is either wired in or deleted
20. ClosePositionDialog.tsx is either wired in or deleted
21. FormulaInput.tsx is either wired in or deleted

### General
22. No backend code modified
23. Nothing inside /studio modified (except BUILDER_OUTPUT.md)

---

## Required Output

When complete, write BUILDER_OUTPUT.md to this task's directory:
/studio/TASKS/TASK-022-frontend-bugfixes/BUILDER_OUTPUT.md

Use the template from /studio/AGENTS/builder/OUTPUT_TEMPLATE.md
Fill in EVERY section. Leave nothing blank.
