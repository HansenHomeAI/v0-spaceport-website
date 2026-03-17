import { expect, test } from '@playwright/test';

const email = process.env.TEST_EMAIL;
const password = process.env.TEST_PASSWORD;
const previewUrl = process.env.PREVIEW_URL;

const requireEnv = () => {
  if (!email || !password || !previewUrl) {
    test.skip(true, 'PREVIEW_URL, TEST_EMAIL, and TEST_PASSWORD must be set');
  }
};

async function loginAndOpenNewProjectModal(page: import('@playwright/test').Page) {
  await page.goto('/create');
  await page.getByRole('button', { name: 'Login' }).click();
  await page.getByPlaceholder(/email/i).fill(email!);
  await page.getByPlaceholder(/password/i).fill(password!);
  await page.getByRole('button', { name: 'Sign in' }).click();

  const saveAndSignIn = page.getByRole('button', { name: 'Save and sign in' });
  const newPasswordInput = page.getByPlaceholder(/new password/i);
  const needsPassword = await newPasswordInput
    .waitFor({ state: 'visible', timeout: 10_000 })
    .then(() => true)
    .catch(() => false);

  if (needsPassword) {
    const suffix = Date.now().toString().slice(-4);
    await newPasswordInput.fill(`Flight3d${suffix}Aa!`);
    await page.getByPlaceholder(/handle/i).fill(`flight3d${Date.now()}`);
    await saveAndSignIn.click();
    await expect(saveAndSignIn).not.toBeVisible({ timeout: 20_000 });
  }

  await expect(page.getByText('New Project')).toBeVisible({ timeout: 20_000 });
  await page.locator('.new-project-card').click();
  await expect(page.locator('#newProjectPopup')).toBeVisible();
}

test('new project modal shows flight path previews in interactive 3d', async ({ page }) => {
  requireEnv();

  await loginAndOpenNewProjectModal(page);

  await page.locator('#address-search').fill('39.739200, -104.990300');
  await page.locator('#address-search').press('Enter');
  await page.getByPlaceholder('Duration').fill('20');
  await page.getByPlaceholder('Quantity').fill('2');
  await page.getByPlaceholder('Minimum').fill('120');

  await page.locator('.battery-view-btn').first().click();
  await expect(page.locator('.battery-view-btn.active')).toHaveCount(1, { timeout: 30_000 });
  await expect(page.getByRole('button', { name: '3D' })).toBeVisible();

  await page.getByRole('button', { name: '3D' }).click();
  await expect(page.locator('[data-flight-path-mode="3d"]')).toBeVisible({ timeout: 30_000 });
  await expect(page.locator('[data-flight-path-3d="ready"]')).toBeVisible();
  await expect(page.locator('.flight-path-3d-title')).toContainText('3D Flight Path');

  const canvas = page.locator('.flight-path-3d-viewer canvas');
  await expect(canvas).toBeVisible();
  const bounds = await canvas.boundingBox();
  expect(bounds).not.toBeNull();
  if (bounds) {
    const centerX = bounds.x + bounds.width / 2;
    const centerY = bounds.y + bounds.height / 2;
    await page.mouse.move(centerX, centerY);
    await page.mouse.down();
    await page.mouse.move(centerX + 140, centerY - 60, { steps: 18 });
    await page.mouse.up();
  }

  await page.getByRole('button', { name: '2D' }).click();
  await expect(page.locator('[data-flight-path-mode="3d"]')).toHaveCount(0);
});
