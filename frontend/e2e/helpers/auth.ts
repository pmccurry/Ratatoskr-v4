import { Page } from '@playwright/test';

export async function login(
  page: Page,
  email = 'admin@ratatoskr.local',
  password = 'changeme123456',
) {
  await page.goto('/login');
  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Password').fill(password);
  await page.getByRole('button', { name: /log in/i }).click();
  await page.waitForURL('**/dashboard', { timeout: 10000 });
}
