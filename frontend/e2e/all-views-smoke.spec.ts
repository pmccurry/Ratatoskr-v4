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
      page.on('console', (msg) => {
        if (msg.type() === 'error') {
          errors.push(msg.text());
        }
      });

      await page.goto(route);
      await page.waitForTimeout(3000);

      const realErrors = errors.filter(
        (e) =>
          !e.includes('favicon') &&
          !e.includes('Future Flag') &&
          !e.includes('net::ERR') &&
          !e.includes('404') &&
          !e.includes('Failed to fetch')
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
});
