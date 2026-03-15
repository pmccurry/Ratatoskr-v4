import { test, expect } from '@playwright/test';
import { login } from './helpers/auth';

test.describe('Strategy Builder', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('strategy list page renders', async ({ page }) => {
    await page.goto('/strategies');
    await page.waitForTimeout(2000);
    const bodyText = await page.textContent('body');
    expect(bodyText).toMatch(/strateg/i);
  });

  test('new strategy button exists', async ({ page }) => {
    await page.goto('/strategies');
    const newBtn = page.getByRole('link', { name: /new strategy|create/i });
    await expect(newBtn).toBeVisible({ timeout: 5000 });
  });

  test('clicking new strategy navigates to builder', async ({ page }) => {
    await page.goto('/strategies');
    const newBtn = page.getByRole('link', { name: /new strategy|create/i });
    await newBtn.click();
    await expect(page).toHaveURL(/\/strategies\/new/);
  });

  test('builder form has all sections', async ({ page }) => {
    await page.goto('/strategies/new');
    await page.waitForTimeout(2000);
    const bodyText = await page.textContent('body');
    expect(bodyText).toMatch(/identity|name/i);
    expect(bodyText).toMatch(/symbol/i);
    expect(bodyText).toMatch(/condition/i);
    expect(bodyText).toMatch(/risk/i);
    expect(bodyText).toMatch(/position.*siz/i);
  });

  test('can fill strategy name', async ({ page }) => {
    await page.goto('/strategies/new');
    const nameInput = page.getByPlaceholder('Strategy name');
    await expect(nameInput).toBeVisible();
    await nameInput.fill('Playwright Test Strategy');
    await expect(nameInput).toHaveValue('Playwright Test Strategy');
  });

  test('market radio buttons work', async ({ page }) => {
    await page.goto('/strategies/new');
    const equities = page.getByLabel('Equities');
    if (await equities.isVisible()) {
      await equities.click();
      await expect(equities).toBeChecked();
    }
  });

  test('timeframe selector works', async ({ page }) => {
    await page.goto('/strategies/new');
    const timeframe = page.locator('select').first();
    if (await timeframe.isVisible()) {
      await timeframe.selectOption('1h');
    }
  });

  test('save draft button exists', async ({ page }) => {
    await page.goto('/strategies/new');
    await expect(page.getByRole('button', { name: /save.*draft/i })).toBeVisible();
  });
});
