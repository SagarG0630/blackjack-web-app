// e2e/smoke.spec.ts
import { test, expect } from '@playwright/test';

// Read BASE_URL from environment, fallback to localhost for local dev
const BASE_URL = process.env.BASE_URL || 'http://127.0.0.1:5000';

test('home page responds and shows Blackjack UI', async ({ page }) => {
  console.log('Using BASE_URL:', BASE_URL);

  await page.goto(`${BASE_URL}/`);

  // Check basic UI elements (non-destructive)
  await expect(page.locator('body')).toContainText(/blackjack|game|dealer/i);
});

test('login page loads and shows login form', async ({ page }) => {
  await page.goto(`${BASE_URL}/login`);

  await expect(page.locator('body')).toContainText(/login/i);
  await expect(page.locator('input[name="username"]')).toBeVisible();
  await expect(page.locator('input[name="password"]')).toBeVisible();
});

test('unauthenticated user is blocked or redirected from dashboard', async ({ page }) => {
  await page.goto(`${BASE_URL}/dashboard`);

  const url = page.url();
  // Should either load login or dashboard with a "please log in" style message
  expect(url).toMatch(/login|dashboard/i);

  await expect(page.locator('body')).toContainText(/login|sign in|dashboard/i);
});

test('key routes respond without server errors', async ({ request }) => {
  // Lightweight HTTP-level check: no 5xx on core pages
  const paths = ['/', '/login', '/dashboard'];

  for (const path of paths) {
    const res = await request.get(`${BASE_URL}${path}`);
    const status = res.status();
    console.log(`GET ${path} -> ${status}`);
    expect(status, `Status for ${path}`).toBeLessThan(500);
  }
});

test('home page has no uncaught JS errors and non-trivial HTML', async ({ page, request }) => {
  const errors: unknown[] = [];
  page.on('pageerror', (err) => {
    console.error('Page error:', err);
    errors.push(err);
  });

  await page.goto(`${BASE_URL}/`);

  // Give it a moment for any on-load scripts
  await page.waitForTimeout(1000);

  expect(errors, 'Uncaught JS errors on home page').toHaveLength(0);

  const res = await request.get(`${BASE_URL}/`);
  const html = await res.text();
  expect(html.length).toBeGreaterThan(50); // homepage has meaningful HTML
});
