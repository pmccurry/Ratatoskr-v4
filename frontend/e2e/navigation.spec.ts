import { test, expect } from '@playwright/test';
import { login } from './helpers/auth';

test.describe('Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('sidebar shows all navigation items', async ({ page }) => {
    await expect(page.getByRole('link', { name: 'Dashboard' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Strategies' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Signals' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Orders' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Portfolio' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Risk' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'System' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Settings' })).toBeVisible();
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
    test(`${route.name} page renders without blank screen`, async ({ page }) => {
      await page.goto(route.url);
      await page.waitForTimeout(2000);
      const bodyText = await page.textContent('body');
      expect(bodyText?.trim().length).toBeGreaterThan(0);
    });
  }

  test('404 page renders for unknown route', async ({ page }) => {
    await page.goto('/this-route-does-not-exist');
    await expect(page.getByText(/404|not found|page not found/i)).toBeVisible({ timeout: 5000 });
  });
});
