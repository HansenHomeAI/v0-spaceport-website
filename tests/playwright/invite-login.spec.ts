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

  const saveAndSignIn = page.getByRole('button', { name: 'Save and sign in' });
  const newPasswordInput = page.getByPlaceholder(/new password/i);
  const needsPassword = await newPasswordInput
    .waitFor({ state: 'visible', timeout: 10_000 })
    .then(() => true)
    .catch(() => false);

  if (needsPassword) {
    const finalPassword = buildNewPassword();
    const handle = `autobot${Date.now()}`;

    await newPasswordInput.fill(finalPassword);
    await page.getByPlaceholder(/handle/i).fill(handle);
    await saveAndSignIn.click();

    await expect(saveAndSignIn).not.toBeVisible({ timeout: 20_000 });
  }

  await expect(page.getByText('New Project')).toBeVisible({ timeout: 20_000 });
});
