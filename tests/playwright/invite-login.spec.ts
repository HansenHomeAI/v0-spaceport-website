import { test, expect } from '@playwright/test';

const email = process.env.TEST_EMAIL;
const tempPassword = process.env.TEST_PASSWORD;

const ensureCredentials = () => {
  if (!email || !tempPassword) {
    test.skip(true, 'TEST_EMAIL and TEST_PASSWORD environment variables are required');
  }
};

const buildNewPassword = () => {
  const stamp = Date.now().toString().slice(-4);
  return `Final${stamp}Aa!`;
};

test('invitee can sign in, finish setup, and reach dashboard', async ({ page }) => {
  ensureCredentials();

  await page.goto('/create');
  await page.fill('input[placeholder="Email"]', email!);
  await page.fill('input[placeholder="Password"]', tempPassword!);
  await page.click('button:has-text("Sign in")');

  await expect(page.getByText('Finish setup by choosing your password')).toBeVisible();

  const finalPassword = buildNewPassword();
  const handle = `autobot${Date.now()}`;

  await page.fill('input[placeholder="New password"]', finalPassword);
  await page.fill('input[placeholder="Handle (e.g. johndoe)"]', handle);
  await page.click('button:has-text("Save and sign in")');

  await expect(page.getByText('Save and sign in')).not.toBeVisible({ timeout: 20_000 });

  await expect(page.getByText('New Project')).toBeVisible();
});
