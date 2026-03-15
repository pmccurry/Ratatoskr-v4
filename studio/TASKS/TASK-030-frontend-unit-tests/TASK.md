# TASK-030 — Frontend Unit Tests (Vitest)

## Goal

Set up vitest infrastructure and write unit tests for frontend utility functions, display components, and UI state management. These tests verify the formatter logic (which had real bugs), component rendering with various props, and Zustand store behavior.

## Depends On

TASK-029

## Scope

**In scope:**
- Vitest configuration (`vitest.config.ts` or config in `vite.config.ts`)
- Test setup file (jsdom, testing-library, custom matchers)
- `lib/formatters.ts` — comprehensive tests for all formatter functions
- `lib/store.ts` — Zustand UI store tests
- `components/` — display component render tests (StatusPill, PnlValue, PriceValue, PercentValue, TimeAgo, EmptyState, ErrorState, ErrorBoundary)
- `features/auth/` — AuthGuard and AdminGuard render logic

**Out of scope:**
- Playwright browser tests (separate task)
- Backend code
- E2E or integration tests
- Application code changes

---

## Deliverables

### D1 — Vitest configuration

Add vitest config. If `vite.config.ts` already exists, add the `test` block there. Otherwise create `vitest.config.ts`:

```typescript
/// <reference types="vitest" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/__tests__/setup.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
    css: false,  // don't process CSS in tests
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
});
```

Ensure these dev dependencies are in `package.json` (add if missing):
- vitest
- @testing-library/react
- @testing-library/jest-dom
- @testing-library/user-event
- jsdom

### D2 — Test setup file (`src/__tests__/setup.ts`)

```typescript
import '@testing-library/jest-dom';

// Mock window.matchMedia for components that use media queries
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }),
});
```

### D3 — `src/__tests__/lib/formatters.test.ts`

Comprehensive tests for every function in `formatters.ts`. These are the highest-value tests — formatters had real bugs (null crashes in TASK-024, negative sign in TASK-025).

**toNumber helper:**

```typescript
describe('toNumber', () => {
  test('returns number for valid number', () => { expect(toNumber(42)).toBe(42); });
  test('returns number for negative', () => { expect(toNumber(-5.5)).toBe(-5.5); });
  test('returns number for zero', () => { expect(toNumber(0)).toBe(0); });
  test('parses string to number', () => { expect(toNumber("12.5")).toBe(12.5); });
  test('parses negative string', () => { expect(toNumber("-3.14")).toBe(-3.14); });
  test('returns null for null', () => { expect(toNumber(null)).toBeNull(); });
  test('returns null for undefined', () => { expect(toNumber(undefined)).toBeNull(); });
  test('returns null for NaN', () => { expect(toNumber(NaN)).toBeNull(); });
  test('returns null for non-numeric string', () => { expect(toNumber("abc")).toBeNull(); });
  test('returns null for empty string', () => { expect(toNumber("")).toBeNull(); });
  test('returns null for object', () => { expect(toNumber({})).toBeNull(); });
  test('returns null for boolean', () => { expect(toNumber(true)).toBeNull(); });
});
```

**formatPnl:**

```typescript
describe('formatPnl', () => {
  test('positive number has + sign and $', () => { expect(formatPnl(50)).toBe('+$50.00'); });
  test('negative number has - sign and $', () => { expect(formatPnl(-50)).toBe('-$50.00'); });
  test('zero shows +$0.00', () => { expect(formatPnl(0)).toBe('+$0.00'); });
  test('large number with commas', () => { expect(formatPnl(1234567)).toContain('1,234,567'); });
  test('small decimal', () => { expect(formatPnl(0.01)).toBe('+$0.01'); });
  test('null returns em dash', () => { expect(formatPnl(null)).toBe('—'); });
  test('undefined returns em dash', () => { expect(formatPnl(undefined)).toBe('—'); });
  test('NaN returns em dash', () => { expect(formatPnl(NaN)).toBe('—'); });
  test('string number is parsed', () => { expect(formatPnl("100")).toBe('+$100.00'); });
  test('negative string number', () => { expect(formatPnl("-25.5")).toBe('-$25.50'); });
});
```

**formatPercent:**

```typescript
describe('formatPercent', () => {
  test('positive has + sign and %', () => { expect(formatPercent(12.5)).toBe('+12.50%'); });
  test('negative has - sign and %', () => { expect(formatPercent(-12.5)).toBe('-12.50%'); });
  test('zero shows +0.00%', () => { expect(formatPercent(0)).toBe('+0.00%'); });
  test('null returns em dash', () => { expect(formatPercent(null)).toBe('—'); });
  test('string number parsed', () => { expect(formatPercent("5.5")).toBe('+5.50%'); });
});
```

**Apply the same pattern to every exported function:** formatCurrency, formatNumber, formatPrice, formatQty, formatTimestamp, etc. Each function gets:
- Happy path (positive, negative, zero)
- Null/undefined/NaN → em dash
- String numbers → parsed and formatted

**If `toNumber` is not exported** (internal helper), test it indirectly through the public functions.

### D4 — `src/__tests__/lib/store.test.ts`

Test the Zustand UI store.

```typescript
import { useUIStore } from '@/lib/store';

describe('UIStore', () => {
  beforeEach(() => {
    // Reset store between tests
    useUIStore.setState(useUIStore.getInitialState());
  });

  test('sidebar starts expanded', () => {
    expect(useUIStore.getState().sidebarCollapsed).toBe(false);
  });

  test('toggleSidebar flips state', () => {
    useUIStore.getState().toggleSidebar();
    expect(useUIStore.getState().sidebarCollapsed).toBe(true);
    useUIStore.getState().toggleSidebar();
    expect(useUIStore.getState().sidebarCollapsed).toBe(false);
  });

  test('equityCurvePeriod defaults to 30d', () => {
    expect(useUIStore.getState().equityCurvePeriod).toBe('30d');
  });

  test('equityCurvePeriod can be updated', () => {
    // Test the setter if one exists
  });

  test('activityFeedPaused defaults to false', () => {
    expect(useUIStore.getState().activityFeedPaused).toBe(false);
  });
});
```

Adapt to the actual store shape — the spec defines `sidebarCollapsed`, `signalFilters`, `orderFilters`, `equityCurvePeriod`, `activityFeedPaused`. Test whatever fields and actions exist.

### D5 — `src/__tests__/components/StatusPill.test.tsx`

```typescript
import { render, screen } from '@testing-library/react';
import { StatusPill } from '@/components/StatusPill';

describe('StatusPill', () => {
  test('renders status text', () => {
    render(<StatusPill status="enabled" />);
    expect(screen.getByText('enabled')).toBeInTheDocument();
  });

  test('enabled status has green styling', () => {
    const { container } = render(<StatusPill status="enabled" />);
    // Check for green-related class (bg-success, text-success, etc.)
    expect(container.firstChild).toHaveClass(/green|success/);
  });

  test('disabled status has gray styling', () => {
    const { container } = render(<StatusPill status="disabled" />);
    expect(container.firstChild).toHaveClass(/gray|muted/);
  });

  test('error status has red styling', () => {
    const { container } = render(<StatusPill status="error" />);
    expect(container.firstChild).toHaveClass(/red|error|danger/);
  });

  test('paused status has yellow styling', () => {
    const { container } = render(<StatusPill status="paused" />);
    expect(container.firstChild).toHaveClass(/yellow|warning/);
  });

  test('draft status has blue styling', () => {
    const { container } = render(<StatusPill status="draft" />);
    expect(container.firstChild).toHaveClass(/blue|info|accent/);
  });
});
```

### D6 — `src/__tests__/components/PnlValue.test.tsx`

```typescript
describe('PnlValue', () => {
  test('renders positive value with green color', () => {
    render(<PnlValue value={100} />);
    const el = screen.getByText(/\+\$100/);
    expect(el).toHaveClass(/green|success|text-success/);
  });

  test('renders negative value with red color', () => {
    render(<PnlValue value={-100} />);
    const el = screen.getByText(/-\$100/);
    expect(el).toHaveClass(/red|error|text-error/);
  });

  test('renders null as em dash', () => {
    render(<PnlValue value={null} />);
    expect(screen.getByText('—')).toBeInTheDocument();
  });

  test('uses monospace font', () => {
    const { container } = render(<PnlValue value={50} />);
    expect(container.firstChild).toHaveClass(/mono/);
  });
});
```

### D7 — `src/__tests__/components/EmptyState.test.tsx`

```typescript
describe('EmptyState', () => {
  test('renders message text', () => {
    render(<EmptyState message="No strategies yet." />);
    expect(screen.getByText('No strategies yet.')).toBeInTheDocument();
  });

  test('renders action button when provided', () => {
    render(<EmptyState message="No data." action="Create" onAction={() => {}} />);
    expect(screen.getByText('Create')).toBeInTheDocument();
  });

  test('calls onAction when button clicked', async () => {
    const handler = vi.fn();
    render(<EmptyState message="No data." action="Create" onAction={handler} />);
    await userEvent.click(screen.getByText('Create'));
    expect(handler).toHaveBeenCalledOnce();
  });

  test('does not render button without action prop', () => {
    render(<EmptyState message="No data." />);
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });
});
```

### D8 — `src/__tests__/components/ErrorBoundary.test.tsx`

```typescript
describe('ErrorBoundary', () => {
  // Suppress React error boundary console output during tests
  const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

  afterAll(() => consoleSpy.mockRestore());

  const ThrowingComponent = () => { throw new Error('Test crash'); };

  test('renders children when no error', () => {
    render(
      <ErrorBoundary>
        <div>Child content</div>
      </ErrorBoundary>
    );
    expect(screen.getByText('Child content')).toBeInTheDocument();
  });

  test('renders fallback on child error', () => {
    render(
      <ErrorBoundary>
        <ThrowingComponent />
      </ErrorBoundary>
    );
    expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();
  });

  test('shows error message in fallback', () => {
    render(
      <ErrorBoundary>
        <ThrowingComponent />
      </ErrorBoundary>
    );
    expect(screen.getByText('Test crash')).toBeInTheDocument();
  });

  test('try again button resets error state', async () => {
    // This is tricky — the component will re-throw on re-render
    // Test that the button exists and is clickable
    render(
      <ErrorBoundary>
        <ThrowingComponent />
      </ErrorBoundary>
    );
    expect(screen.getByText(/try again/i)).toBeInTheDocument();
  });

  test('renders custom fallback when provided', () => {
    render(
      <ErrorBoundary fallback={<div>Custom error</div>}>
        <ThrowingComponent />
      </ErrorBoundary>
    );
    expect(screen.getByText('Custom error')).toBeInTheDocument();
  });
});
```

### D9 — `src/__tests__/components/ErrorState.test.tsx`

```typescript
describe('ErrorState', () => {
  test('renders error message', () => {
    render(<ErrorState message="Failed to load." />);
    expect(screen.getByText('Failed to load.')).toBeInTheDocument();
  });

  test('renders retry button', () => {
    render(<ErrorState message="Error" onRetry={() => {}} />);
    expect(screen.getByText(/retry/i)).toBeInTheDocument();
  });

  test('calls onRetry when clicked', async () => {
    const handler = vi.fn();
    render(<ErrorState message="Error" onRetry={handler} />);
    await userEvent.click(screen.getByText(/retry/i));
    expect(handler).toHaveBeenCalledOnce();
  });
});
```

### D10 — `src/__tests__/components/TimeAgo.test.tsx`

```typescript
describe('TimeAgo', () => {
  test('renders "just now" for recent timestamp', () => {
    render(<TimeAgo value={new Date().toISOString()} />);
    expect(screen.getByText(/just now|0s|<1m/i)).toBeInTheDocument();
  });

  test('renders minutes for older timestamp', () => {
    const fiveMinAgo = new Date(Date.now() - 5 * 60 * 1000).toISOString();
    render(<TimeAgo value={fiveMinAgo} />);
    expect(screen.getByText(/5m|5 min/i)).toBeInTheDocument();
  });

  test('renders hours for old timestamp', () => {
    const twoHoursAgo = new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString();
    render(<TimeAgo value={twoHoursAgo} />);
    expect(screen.getByText(/2h|2 hour/i)).toBeInTheDocument();
  });

  test('renders null/undefined gracefully', () => {
    render(<TimeAgo value={null} />);
    // Should render "—" or "never" or empty, not crash
    expect(screen.queryByText(/error/i)).not.toBeInTheDocument();
  });
});
```

### D11 — `src/__tests__/features/auth/AuthGuard.test.tsx`

```typescript
describe('AuthGuard', () => {
  // Mock the auth hook
  vi.mock('@/features/auth/useAuth', () => ({
    useAuth: vi.fn(),
  }));

  test('renders children when authenticated', () => {
    (useAuth as Mock).mockReturnValue({ isAuthenticated: true, user: { role: 'admin' } });
    render(
      <MemoryRouter>
        <AuthGuard><div>Protected content</div></AuthGuard>
      </MemoryRouter>
    );
    expect(screen.getByText('Protected content')).toBeInTheDocument();
  });

  test('redirects to login when not authenticated', () => {
    (useAuth as Mock).mockReturnValue({ isAuthenticated: false, user: null });
    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <Routes>
          <Route path="/dashboard" element={<AuthGuard><div>Protected</div></AuthGuard>} />
          <Route path="/login" element={<div>Login page</div>} />
        </Routes>
      </MemoryRouter>
    );
    expect(screen.getByText('Login page')).toBeInTheDocument();
  });
});
```

### D12 — `src/__tests__/components/PercentValue.test.tsx` and `PriceValue.test.tsx`

Quick render tests for these display components:

```typescript
describe('PercentValue', () => {
  test('renders formatted percent', () => {
    render(<PercentValue value={12.5} />);
    expect(screen.getByText(/12\.50%/)).toBeInTheDocument();
  });

  test('renders null as em dash', () => {
    render(<PercentValue value={null} />);
    expect(screen.getByText('—')).toBeInTheDocument();
  });

  test('positive has green color', () => { /* check class */ });
  test('negative has red color', () => { /* check class */ });
});

describe('PriceValue', () => {
  test('renders formatted price', () => {
    render(<PriceValue value={150.50} />);
    expect(screen.getByText(/150\.50/)).toBeInTheDocument();
  });

  test('uses monospace font', () => { /* check class */ });
  test('renders null as em dash', () => { /* check for — */ });
});
```

---

## Acceptance Criteria

| # | Criterion |
|---|-----------|
| AC1 | Vitest config exists and uses jsdom environment |
| AC2 | Test setup file configures @testing-library/jest-dom matchers |
| AC3 | Dev dependencies include vitest, @testing-library/react, @testing-library/jest-dom, jsdom |
| AC4 | Every exported function in `formatters.ts` has at least 5 test cases (positive, negative, zero, null, string) |
| AC5 | `formatPnl` tests verify correct sign: `formatPnl(-50)` → `'-$50.00'`, `formatPnl(50)` → `'+$50.00'` |
| AC6 | `formatPercent` tests verify correct sign: `formatPercent(-12.5)` → `'-12.50%'` |
| AC7 | All formatter null-guard tests verify em dash (`'—'`) return for null, undefined, and NaN |
| AC8 | Zustand store tests verify sidebar toggle, default period, and state reset |
| AC9 | StatusPill renders correct color class for each status (enabled, disabled, paused, error, draft) |
| AC10 | PnlValue renders green for positive, red for negative, em dash for null |
| AC11 | EmptyState renders message and optional action button |
| AC12 | ErrorBoundary renders children normally and shows fallback on crash |
| AC13 | ErrorState renders message and retry button |
| AC14 | TimeAgo renders relative time strings and handles null gracefully |
| AC15 | AuthGuard renders children when authenticated and redirects when not |
| AC16 | `npm run test` (or `npx vitest run`) collects all tests without import errors |
| AC17 | No application code modified |
| AC18 | Nothing inside /studio modified (except BUILDER_OUTPUT.md) |

---

## Files to Create

| File | Purpose |
|------|---------|
| `frontend/src/__tests__/setup.ts` | Test setup (jest-dom matchers, matchMedia mock) |
| `frontend/src/__tests__/lib/formatters.test.ts` | Formatter function tests |
| `frontend/src/__tests__/lib/store.test.ts` | Zustand store tests |
| `frontend/src/__tests__/components/StatusPill.test.tsx` | Status pill render tests |
| `frontend/src/__tests__/components/PnlValue.test.tsx` | PnL display tests |
| `frontend/src/__tests__/components/PercentValue.test.tsx` | Percent display tests |
| `frontend/src/__tests__/components/PriceValue.test.tsx` | Price display tests |
| `frontend/src/__tests__/components/EmptyState.test.tsx` | Empty state render tests |
| `frontend/src/__tests__/components/ErrorBoundary.test.tsx` | Error boundary tests |
| `frontend/src/__tests__/components/ErrorState.test.tsx` | Error state render tests |
| `frontend/src/__tests__/components/TimeAgo.test.tsx` | Relative time display tests |
| `frontend/src/__tests__/features/auth/AuthGuard.test.tsx` | Auth guard render tests |

## Files to Modify

| File | What Changes |
|------|-------------|
| `frontend/vite.config.ts` (or new `vitest.config.ts`) | Add vitest test config |
| `frontend/package.json` | Add test dev dependencies and `"test"` script if missing |

## Files NOT to Touch

- `frontend/src/` application code (components, pages, features, lib)
- Backend code
- Studio files

---

## Builder Notes

- **Import paths:** Components may use `@/` alias or relative paths. Check `tsconfig.json` and `vite.config.ts` for alias configuration. The test config must mirror the same aliases.
- **Component props:** The test descriptions above use assumed prop names. Inspect the actual component files to determine exact prop names and types. Adapt tests to match.
- **CSS class assertions:** Class name checks (e.g., "has green styling") depend on the actual Tailwind classes used. Use regex matchers like `toHaveClass(/success|green/)` or check `className` includes the expected string.
- **Mocking:** AuthGuard tests need to mock `useAuth`. Use `vi.mock()` with the correct import path.
- **Store reset:** Zustand stores persist between tests unless reset. Use `beforeEach` to reset via `useStore.setState(initialState)` or `useStore.getInitialState()`.
- **If a component doesn't exist or has different props** than expected: skip that test file and document it in BUILDER_OUTPUT.md. Don't create test files for nonexistent components.
- **Test script:** Add `"test": "vitest run"` and `"test:watch": "vitest"` to package.json scripts if not present.

## References

- cross_cutting_specs.md §6 — Testing Strategy ("vitest: component and logic unit tests")
- frontend_specs.md §8 — Folder Structure (component locations)
- frontend_specs.md §Data Display Components (StatusPill, PnlValue, etc.)
- frontend_specs.md §7 — State Management (Zustand store shape)
- frontend_specs.md §11 — Loading, Empty, and Error States
