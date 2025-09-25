import { test, expect } from '@playwright/test';

const email = process.env.TEST_EMAIL;
const tempPassword = process.env.TEST_PASSWORD;

const requireEmployeeCreds = () => {
  if (!email || !tempPassword) {
    test.skip(true, 'TEST_EMAIL and TEST_PASSWORD environment variables are required');
  }
};

const buildNewPassword = () => {
  const suffix = Date.now().toString().slice(-4);
  return `Deliver${suffix}Aa!`;
};

test('employee can access delivery controls', async ({ page }) => {
  requireEmployeeCreds();

  page.on('console', (message) => {
    console.log('browser console:', message.text());
  });

  page.on('response', async (response) => {
    const url = response.url();
    if (url.includes('/admin/model-delivery/')) {
      console.log('model-delivery response', response.status(), url);
    }
  });

  await page.goto('/create');
  await page.getByRole('button', { name: 'Login' }).click();
  await page.getByPlaceholder(/email/i).fill(email!);
  await page.getByPlaceholder(/password/i).fill(tempPassword!);
  await page.click('button:has-text("Sign in")');

  const finishSetup = page.getByText('Finish setup by choosing your password');
  if (await finishSetup.isVisible({ timeout: 5_000 }).catch(() => false)) {
    const finalPassword = buildNewPassword();
    const handle = `employee${Date.now()}`;

    await page.getByPlaceholder(/new password/i).fill(finalPassword);
    await page.getByPlaceholder(/handle/i).fill(handle);
    await page.click('button:has-text("Save and sign in")');

    await expect(page.getByText('Save and sign in')).not.toBeVisible({ timeout: 20_000 });
  }

  await page.waitForTimeout(2000);

  await expect(page.getByText('New Project')).toBeVisible({ timeout: 20_000 });
  console.log('model delivery trigger count', await page.locator('.model-delivery-trigger').count());
  await expect(page.getByRole('button', { name: 'Send Model Link' })).toBeVisible();
  await expect(page.getByText('Beta Access Management')).toBeVisible();

  await page.getByRole('button', { name: 'Send Model Link' }).click();
  await expect(page.getByRole('dialog', { name: 'Send Model Link' })).toBeVisible();
  await page.getByRole('button', { name: 'Cancel' }).click();
  await expect(page.getByRole('dialog', { name: 'Send Model Link' })).not.toBeVisible();
});
