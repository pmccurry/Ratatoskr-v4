import { test, expect } from '@playwright/test';
import { login } from './helpers/auth';

test.describe('Authentication', () => {
  test('login page renders with form fields', async ({ page }) => {
    await page.goto('/login');
    await expect(page.getByLabel('Email')).toBeVisible();
    await expect(page.getByLabel('Password')).toBeVisible();
    await expect(page.getByRole('button', { name: /log in/i })).toBeVisible();
  });

  test('login page has dark theme', async ({ page }) => {
    await page.goto('/login');
    const bgColor = await page.evaluate(() =>
      getComputedStyle(document.body).backgroundColor
    );
    expect(bgColor).not.toBe('rgb(255, 255, 255)');
  });

  test('login with valid credentials redirects to dashboard', async ({ page }) => {
    await login(page);
    await expect(page).toHaveURL(/\/dashboard/);
  });

  test('login with wrong password shows error', async ({ page }) => {
    await page.goto('/login');
    await page.getByLabel('Email').fill('admin@ratatoskr.local');
    await page.getByLabel('Password').fill('wrongpassword123');
    await page.getByRole('button', { name: /log in/i }).click();
    await expect(page.locator('.text-error, [class*="error"]').first()).toBeVisible({ timeout: 5000 });
    await expect(page).toHaveURL(/\/login/);
  });

  test('unauthenticated user redirected to login', async ({ page }) => {
    await page.goto('/dashboard');
    await expect(page).toHaveURL(/\/login/);
  });
});
