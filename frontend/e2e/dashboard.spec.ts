import { test, expect } from '@playwright/test';
import { login } from './helpers/auth';

test.describe('Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto('/dashboard');
  });

  test('page title is visible', async ({ page }) => {
    await expect(page.getByText('Dashboard')).toBeVisible();
  });

  test('stat cards section exists', async ({ page }) => {
    // Stat cards show labels like "Total Equity", "Today's PnL", etc.
    // With no data, they show em dashes
    await page.waitForTimeout(2000);
    const bodyText = await page.textContent('body');
    expect(bodyText).toMatch(/equity|pnl|positions|drawdown/i);
  });

  test('strategy status section exists', async ({ page }) => {
    // May show "No strategies" or a strategy list
    await page.waitForTimeout(2000);
    const bodyText = await page.textContent('body');
    expect(bodyText).toMatch(/strateg/i);
  });

  test('activity feed section exists', async ({ page }) => {
    await page.waitForTimeout(2000);
    const bodyText = await page.textContent('body');
    expect(bodyText).toMatch(/activity|recent|no recent/i);
  });

  test('no blank screen', async ({ page }) => {
    const bodyText = await page.textContent('body');
    expect(bodyText?.trim().length).toBeGreaterThan(100);
  });

  test('dark theme — no white background', async ({ page }) => {
    const bgColor = await page.evaluate(() =>
      getComputedStyle(document.body).backgroundColor
    );
    expect(bgColor).not.toBe('rgb(255, 255, 255)');
  });

  test('no console errors on dashboard', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });
    await page.goto('/dashboard');
    await page.waitForTimeout(3000);
    const realErrors = errors.filter(
      (e) =>
        !e.includes('favicon') &&
        !e.includes('Future Flag') &&
        !e.includes('net::ERR') &&
        !e.includes('404')
    );
    expect(realErrors).toHaveLength(0);
  });
});
