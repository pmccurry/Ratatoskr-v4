import { test, expect } from '@playwright/test';
import { login } from './helpers/auth';

test.describe('Risk Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto('/risk');
  });

  test('risk page renders without crash', async ({ page }) => {
    await page.waitForTimeout(2000);
    const bodyText = await page.textContent('body');
    expect(bodyText?.trim().length).toBeGreaterThan(50);
  });

  test('page title is visible', async ({ page }) => {
    await expect(page.getByText('Risk Dashboard')).toBeVisible();
  });

  test('kill switch control is visible', async ({ page }) => {
    const killSwitch = page.getByText(/kill.*switch/i);
    await expect(killSwitch.first()).toBeVisible({ timeout: 5000 });
  });

  test('risk config section exists', async ({ page }) => {
    await page.waitForTimeout(2000);
    const bodyText = await page.textContent('body');
    expect(bodyText).toMatch(/config|exposure|drawdown/i);
  });
});
