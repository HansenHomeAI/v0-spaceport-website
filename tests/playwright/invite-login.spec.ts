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
  await page.getByRole('button', { name: 'Login' }).click();
  await page.getByPlaceholder(/email/i).fill(email!);
  await page.getByPlaceholder(/password/i).fill(tempPassword!);
  await page.click('button:has-text("Sign in")');

  const finishSetup = page.getByText('Finish setup by choosing your password');
  if (await finishSetup.isVisible({ timeout: 5_000 }).catch(() => false)) {
    const finalPassword = buildNewPassword();
    const handle = `autobot${Date.now()}`;

    await page.getByPlaceholder(/new password/i).fill(finalPassword);
    await page.getByPlaceholder(/handle/i).fill(handle);
    await page.click('button:has-text("Save and sign in")');

    await expect(page.getByText('Save and sign in')).not.toBeVisible({ timeout: 20_000 });
  }

  await expect(page.getByText('New Project')).toBeVisible();
});
