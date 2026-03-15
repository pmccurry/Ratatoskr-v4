# TASK-031 — Playwright Browser E2E Tests

## Goal

Write browser-based end-to-end tests using Playwright that exercise the full UI through a real browser. These tests verify that pages render, navigation works, forms submit, and the user can complete key workflows from login through strategy creation. This is the final testing task in Milestone 13.

## Depends On

TASK-030

## Scope

**In scope:**
- Playwright configuration (`playwright.config.ts`)
- Auth flow: login page → submit credentials → redirect to dashboard → logout
- Navigation: every sidebar link renders a page without crashing
- Dashboard: stat cards, charts, and widgets visible (even with empty data)
- Strategy builder: fill form → save draft → strategy appears in list
- Kill switch: activate → verify UI state → deactivate
- Theme: dark theme consistent, no white flash
- Error handling: 404 page renders for unknown routes

**Out of scope:**
- Broker-connected tests (requires live data)
- Backend code changes
- Frontend application code changes
- Visual regression / screenshot comparison
- Performance testing

---

## Deliverables

### D1 — Playwright configuration (`playwright.config.ts`)

Place at `frontend/playwright.config.ts`:

```typescript
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,   // tests share auth state, run sequentially
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  // Start the frontend dev server before tests
  webServer: {
    command: 'npm run dev -- --port 3000',
    port: 3000,
    reuseExistingServer: !process.env.CI,
    timeout: 30000,
  },
});
```

**Note:** Playwright's `webServer` starts the frontend. The backend must be running separately (via `docker compose up` or `start-dev.sh`). Document this in the test README section.

Add to `frontend/package.json` scripts:
```json
"test:e2e": "playwright test",
"test:e2e:headed": "playwright test --headed",
"test:e2e:ui": "playwright test --ui"
```

Add `@playwright/test` to devDependencies.

### D2 — Auth helper (`e2e/helpers/auth.ts`)

Shared login helper to avoid repeating login in every test:

```typescript
import { Page } from '@playwright/test';

export async function login(page: Page, email = 'admin@ratatoskr.local', password = 'changeme123456') {
  await page.goto('/login');
  await page.getByLabel(/email/i).fill(email);
  await page.getByLabel(/password/i).fill(password);
  await page.getByRole('button', { name: /log in|sign in/i }).click();
  // Wait for redirect to dashboard
  await page.waitForURL('**/dashboard', { timeout: 10000 });
}

export async function logout(page: Page) {
  // Click user menu or logout button in sidebar
  await page.getByRole('button', { name: /logout|sign out/i }).click();
  await page.waitForURL('**/login', { timeout: 5000 });
}
```

Adapt selectors to match the actual login form. Use accessible selectors (getByLabel, getByRole, getByText) over CSS selectors wherever possible.

### D3 — `e2e/auth.spec.ts`

```typescript
import { test, expect } from '@playwright/test';
import { login } from './helpers/auth';

test.describe('Authentication', () => {
  test('login page renders with dark theme', async ({ page }) => {
    await page.goto('/login');
    await expect(page.getByLabel(/email/i)).toBeVisible();
    await expect(page.getByLabel(/password/i)).toBeVisible();
    await expect(page.getByRole('button', { name: /log in|sign in/i })).toBeVisible();
    // Dark theme: check background is dark (not white)
    const bgColor = await page.evaluate(() =>
      getComputedStyle(document.body).backgroundColor
    );
    expect(bgColor).not.toBe('rgb(255, 255, 255)');
  });

  test('login with valid credentials redirects to dashboard', async ({ page }) => {
    await login(page);
    await expect(page).toHaveURL(/\/dashboard/);
    // Sidebar should be visible
    await expect(page.getByRole('navigation')).toBeVisible();
  });

  test('login with wrong password shows error', async ({ page }) => {
    await page.goto('/login');
    await page.getByLabel(/email/i).fill('admin@ratatoskr.local');
    await page.getByLabel(/password/i).fill('wrongpassword');
    await page.getByRole('button', { name: /log in|sign in/i }).click();
    // Should show error message, stay on login page
    await expect(page.getByText(/invalid|incorrect|failed/i)).toBeVisible({ timeout: 5000 });
    await expect(page).toHaveURL(/\/login/);
  });

  test('unauthenticated user redirected to login', async ({ page }) => {
    await page.goto('/dashboard');
    await expect(page).toHaveURL(/\/login/);
  });

  test('logout returns to login page', async ({ page }) => {
    await login(page);
    // Find and click logout
    // Adapt selector to actual UI — might be in sidebar footer, user menu, etc.
    const logoutButton = page.getByRole('button', { name: /logout|sign out/i });
    if (await logoutButton.isVisible()) {
      await logoutButton.click();
    } else {
      // Try user menu first
      await page.getByRole('button', { name: /user|profile|account/i }).click();
      await page.getByText(/logout|sign out/i).click();
    }
    await expect(page).toHaveURL(/\/login/, { timeout: 5000 });
  });
});
```

### D4 — `e2e/navigation.spec.ts`

```typescript
import { test, expect } from '@playwright/test';
import { login } from './helpers/auth';

test.describe('Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('sidebar shows all navigation items', async ({ page }) => {
    await expect(page.getByRole('link', { name: /dashboard/i })).toBeVisible();
    await expect(page.getByRole('link', { name: /strategies/i })).toBeVisible();
    await expect(page.getByRole('link', { name: /signals/i })).toBeVisible();
    await expect(page.getByRole('link', { name: /orders/i })).toBeVisible();
    await expect(page.getByRole('link', { name: /portfolio/i })).toBeVisible();
    await expect(page.getByRole('link', { name: /risk/i })).toBeVisible();
    // Admin-only
    await expect(page.getByRole('link', { name: /system/i })).toBeVisible();
    await expect(page.getByRole('link', { name: /settings/i })).toBeVisible();
  });

  const routes = [
    { name: 'Dashboard', url: '/dashboard' },
    { name: 'Strategies', url: '/strategies' },
    { name: 'Signals', url: '/signals' },
    { name: 'Orders', url: '/orders' },
    { name: 'Portfolio', url: '/portfolio' },
    { name: 'Risk', url: '/risk' },
    { name: 'System', url: '/system' },
    { name: 'Settings', url: '/settings' },
  ];

  for (const route of routes) {
    test(`${route.name} page renders without crash`, async ({ page }) => {
      await page.goto(route.url);
      // Page should not show blank screen — check for any visible content
      await expect(page.locator('main, [role="main"], .page-container, [class*="page"]').first())
        .toBeVisible({ timeout: 10000 });
      // No unhandled error in the page
      const errorBoundary = page.getByText(/something went wrong/i);
      // Error boundary is acceptable (means page loaded but data may be missing)
      // Blank screen is NOT acceptable
      const bodyText = await page.textContent('body');
      expect(bodyText?.trim().length).toBeGreaterThan(0);
    });
  }

  test('sidebar collapse/expand works', async ({ page }) => {
    // Find collapse toggle
    const toggle = page.getByRole('button', { name: /collapse|toggle.*sidebar|menu/i });
    if (await toggle.isVisible()) {
      await toggle.click();
      // Sidebar should be collapsed — nav text hidden, icons visible
      await page.waitForTimeout(300); // animation
      await toggle.click();
      // Sidebar should be expanded again
    }
  });

  test('404 page renders for unknown route', async ({ page }) => {
    await page.goto('/this-route-does-not-exist');
    await expect(page.getByText(/404|not found|page not found/i)).toBeVisible({ timeout: 5000 });
  });
});
```

### D5 — `e2e/dashboard.spec.ts`

```typescript
import { test, expect } from '@playwright/test';
import { login } from './helpers/auth';

test.describe('Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto('/dashboard');
  });

  test('stat cards are visible', async ({ page }) => {
    // Should have stat card elements (even with "—" values when no data)
    const statCards = page.locator('[class*="stat-card"], [class*="StatCard"], [data-testid*="stat"]');
    // Fallback: look for card-like containers
    const cards = statCards.count() ? statCards : page.locator('.card, [class*="card"]');
    await expect(cards.first()).toBeVisible({ timeout: 10000 });
  });

  test('equity curve chart area is visible', async ({ page }) => {
    // Look for chart container or recharts SVG
    const chart = page.locator('[class*="chart"], [class*="equity"], .recharts-wrapper, svg.recharts-surface');
    // Chart may show empty state — that's fine
    await page.waitForTimeout(2000); // let charts render
    // At minimum, the chart container section should exist
  });

  test('strategy status list is visible', async ({ page }) => {
    // May show empty state: "No strategies yet"
    const content = page.getByText(/no strategies|strategy|create/i);
    await expect(content.first()).toBeVisible({ timeout: 5000 });
  });

  test('activity feed section exists', async ({ page }) => {
    const feed = page.getByText(/activity|recent|no recent/i);
    await expect(feed.first()).toBeVisible({ timeout: 5000 });
  });

  test('no blank screen — page has content', async ({ page }) => {
    const bodyText = await page.textContent('body');
    expect(bodyText?.trim().length).toBeGreaterThan(100);
  });

  test('dark theme — no white background', async ({ page }) => {
    const bgColor = await page.evaluate(() =>
      getComputedStyle(document.body).backgroundColor
    );
    // Dark theme: background should be dark (not white or near-white)
    expect(bgColor).not.toBe('rgb(255, 255, 255)');
    expect(bgColor).not.toBe('rgba(0, 0, 0, 0)'); // not transparent fallback
  });

  test('no console errors on dashboard', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error' && !msg.text().includes('React Router')) {
        errors.push(msg.text());
      }
    });
    await page.goto('/dashboard');
    await page.waitForTimeout(3000); // let everything load
    // Filter out known benign errors (favicon 404, React Router warnings)
    const realErrors = errors.filter(e =>
      !e.includes('favicon') && !e.includes('Future Flag') && !e.includes('net::ERR')
    );
    expect(realErrors).toHaveLength(0);
  });
});
```

### D6 — `e2e/strategy-builder.spec.ts`

```typescript
import { test, expect } from '@playwright/test';
import { login } from './helpers/auth';

test.describe('Strategy Builder', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('strategy list shows empty state with create button', async ({ page }) => {
    await page.goto('/strategies');
    await expect(page.getByText(/no strategies|create/i).first()).toBeVisible({ timeout: 5000 });
    await expect(page.getByRole('button', { name: /new strategy|create/i })).toBeVisible();
  });

  test('clicking new strategy navigates to builder', async ({ page }) => {
    await page.goto('/strategies');
    await page.getByRole('button', { name: /new strategy|create/i }).click();
    await expect(page).toHaveURL(/\/strategies\/new/);
  });

  test('builder form has all sections', async ({ page }) => {
    await page.goto('/strategies/new');
    // Check for key section headers or labels
    await expect(page.getByText(/identity|name/i).first()).toBeVisible();
    await expect(page.getByText(/symbol/i).first()).toBeVisible();
    await expect(page.getByText(/entry.*condition|condition/i).first()).toBeVisible();
    await expect(page.getByText(/risk.*management|stop.*loss/i).first()).toBeVisible();
    await expect(page.getByText(/position.*siz/i).first()).toBeVisible();
  });

  test('can fill and save a basic strategy', async ({ page }) => {
    await page.goto('/strategies/new');

    // Fill identity
    await page.getByLabel(/name/i).first().fill('Test Playwright Strategy');

    // Select market (radio)
    const equitiesRadio = page.getByLabel(/equities/i);
    if (await equitiesRadio.isVisible()) {
      await equitiesRadio.click();
    }

    // Select timeframe
    const timeframeSelect = page.getByLabel(/timeframe/i);
    if (await timeframeSelect.isVisible()) {
      await timeframeSelect.selectOption('1h');
    }

    // Add at least one symbol (if explicit mode)
    // This depends on the actual UI — may be a text input, search, or dropdown
    const symbolInput = page.getByPlaceholder(/symbol|search/i).first();
    if (await symbolInput.isVisible()) {
      await symbolInput.fill('AAPL');
      // May need to click a suggestion or press Enter
      await page.keyboard.press('Enter');
    }

    // Save draft
    await page.getByRole('button', { name: /save.*draft|save/i }).click();

    // Should redirect to strategy list or detail
    await page.waitForTimeout(2000);
    // Verify strategy appears (either redirected to list or detail page)
    const pageContent = await page.textContent('body');
    expect(pageContent).toContain('Test Playwright Strategy');
  });

  test('strategy appears in list after creation', async ({ page }) => {
    await page.goto('/strategies');
    // If previous test created a strategy, it should appear
    // If no strategies exist, this verifies the empty state
    await page.waitForTimeout(2000);
  });

  test('condition builder add/remove works', async ({ page }) => {
    await page.goto('/strategies/new');

    // Find add condition button
    const addButton = page.getByRole('button', { name: /add.*condition/i });
    if (await addButton.isVisible()) {
      await addButton.click();
      // A new condition row should appear
      await page.waitForTimeout(500);
      // Find remove button and click it
      const removeButton = page.getByRole('button', { name: /remove|delete|🗑/i }).first();
      if (await removeButton.isVisible()) {
        await removeButton.click();
      }
    }
  });
});
```

### D7 — `e2e/risk.spec.ts`

```typescript
import { test, expect } from '@playwright/test';
import { login } from './helpers/auth';

test.describe('Risk Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto('/risk');
  });

  test('risk page renders without crash', async ({ page }) => {
    const bodyText = await page.textContent('body');
    expect(bodyText?.trim().length).toBeGreaterThan(50);
    // Should not show blank screen or error boundary
  });

  test('kill switch control is visible', async ({ page }) => {
    const killSwitch = page.getByText(/kill.*switch|emergency|halt/i);
    await expect(killSwitch.first()).toBeVisible({ timeout: 5000 });
  });

  test('kill switch can be activated and deactivated', async ({ page }) => {
    // Find activate button
    const activateBtn = page.getByRole('button', { name: /activate|enable.*kill|halt/i });
    if (await activateBtn.isVisible()) {
      await activateBtn.click();
      // May show confirmation dialog
      const confirmBtn = page.getByRole('button', { name: /confirm|yes/i });
      if (await confirmBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
        await confirmBtn.click();
      }
      await page.waitForTimeout(1000);

      // Deactivate
      const deactivateBtn = page.getByRole('button', { name: /deactivate|disable.*kill|resume/i });
      if (await deactivateBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
        await deactivateBtn.click();
        const confirmBtn2 = page.getByRole('button', { name: /confirm|yes/i });
        if (await confirmBtn2.isVisible({ timeout: 2000 }).catch(() => false)) {
          await confirmBtn2.click();
        }
      }
    }
  });
});
```

### D8 — `e2e/all-views-smoke.spec.ts`

A fast smoke test that visits every route and verifies no blank screen and no unhandled console errors.

```typescript
import { test, expect } from '@playwright/test';
import { login } from './helpers/auth';

const ALL_ROUTES = [
  '/dashboard',
  '/strategies',
  '/signals',
  '/orders',
  '/portfolio',
  '/risk',
  '/system',
  '/settings',
];

test.describe('All Views Smoke Test', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  for (const route of ALL_ROUTES) {
    test(`${route} has no console errors`, async ({ page }) => {
      const errors: string[] = [];
      page.on('console', msg => {
        if (msg.type() === 'error') {
          errors.push(msg.text());
        }
      });

      await page.goto(route);
      await page.waitForTimeout(3000);

      // Filter benign errors
      const realErrors = errors.filter(e =>
        !e.includes('favicon') &&
        !e.includes('Future Flag') &&
        !e.includes('net::ERR') &&
        !e.includes('404')  // API 404s for missing data are expected
      );
      expect(realErrors).toHaveLength(0);
    });
  }

  test('no white flash during page transitions', async ({ page }) => {
    for (const route of ALL_ROUTES.slice(0, 4)) {
      await page.goto(route);
      const bgColor = await page.evaluate(() =>
        getComputedStyle(document.body).backgroundColor
      );
      expect(bgColor).not.toBe('rgb(255, 255, 255)');
    }
  });

  test('financial numbers use monospace font', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForTimeout(2000);
    // Check any element with mono class exists
    const monoElements = page.locator('[class*="mono"], [style*="monospace"]');
    // It's OK if there are none (no data to display), but if they exist, they should be monospace
  });
});
```

---

## Acceptance Criteria

| # | Criterion |
|---|-----------|
| AC1 | `playwright.config.ts` exists with chromium project and webServer config |
| AC2 | `@playwright/test` is in devDependencies with `test:e2e` script |
| AC3 | Auth helper provides reusable `login()` function using accessible selectors |
| AC4 | Login test: valid credentials → redirect to dashboard |
| AC5 | Login test: wrong password → error message shown, stays on login |
| AC6 | Login test: unauthenticated access → redirect to login |
| AC7 | Navigation test: all 8 sidebar links render pages without blank screens |
| AC8 | Navigation test: 404 page renders for unknown routes |
| AC9 | Dashboard test: stat cards, chart area, strategy list, activity feed sections exist |
| AC10 | Dashboard test: no console errors (filtering benign warnings) |
| AC11 | Strategy builder test: form renders with identity, symbols, conditions, risk, sizing sections |
| AC12 | Strategy builder test: fill form and save draft succeeds (or documents why it can't) |
| AC13 | Kill switch test: control is visible on risk page |
| AC14 | Smoke test: all 8 routes have no unhandled console errors |
| AC15 | Dark theme test: no white background on any page |
| AC16 | No application code modified |
| AC17 | Nothing inside /studio modified (except BUILDER_OUTPUT.md) |

---

## Files to Create

| File | Purpose |
|------|---------|
| `frontend/playwright.config.ts` | Playwright configuration |
| `frontend/e2e/helpers/auth.ts` | Shared login/logout helpers |
| `frontend/e2e/auth.spec.ts` | Authentication flow tests |
| `frontend/e2e/navigation.spec.ts` | Sidebar and route tests |
| `frontend/e2e/dashboard.spec.ts` | Dashboard widget tests |
| `frontend/e2e/strategy-builder.spec.ts` | Strategy form tests |
| `frontend/e2e/risk.spec.ts` | Risk dashboard and kill switch tests |
| `frontend/e2e/all-views-smoke.spec.ts` | Console error smoke test for all routes |

## Files to Modify

| File | What Changes |
|------|-------------|
| `frontend/package.json` | Add `@playwright/test` devDependency and `test:e2e` scripts |

## Files NOT to Touch

- `frontend/src/` application code
- Backend code
- Studio files

---

## Builder Notes

- **Backend must be running.** Playwright tests hit the real frontend which proxies to the real backend. The backend + Postgres must be running before tests start. Either via `docker compose up` or `./scripts/start-dev.sh`.
- **Selectors:** Use Playwright's recommended accessible selectors (`getByRole`, `getByLabel`, `getByText`) as primary selectors. Fall back to CSS selectors only when accessible selectors don't work. Inspect the actual rendered HTML to determine correct selectors.
- **Resilient assertions:** Many tests check for content that may vary (empty states vs populated). Use patterns like `await expect(page.getByText(/no strategies|strategy|create/i).first()).toBeVisible()` that match either state.
- **Timeouts:** Pages with API calls may take a few seconds to render. Use `toBeVisible({ timeout: 10000 })` for elements that depend on API responses.
- **Console error filtering:** Browser console will have benign errors (favicon 404, React Router future flag warnings, failed API calls when no data exists). Filter these in assertions.
- **Sequential execution:** Set `workers: 1` and `fullyParallel: false` since tests share a database and the strategy creation test creates state that later tests may see.
- **If the login form has different selectors:** adapt `getByLabel(/email/i)` etc. to match the actual form. Check what `<label>` or `aria-label` attributes exist.
- **npx playwright install:** The builder should run `npx playwright install chromium` to download the browser binary before running tests.

## References

- cross_cutting_specs.md §6 — Testing Strategy ("Playwright: browser-based end-to-end tests")
- frontend_specs.md §1 — App Shell (sidebar navigation, routes)
- frontend_specs.md §2 — Dashboard (stat cards, equity curve, strategy list, activity feed)
- frontend_specs.md §3 — Strategy Builder (9-section form)
- frontend_specs.md §11 — Loading, Empty, and Error States
- PHASE4_PLAN.md §Stage 4 — Frontend Visual Verification checklist (used as test case basis)
