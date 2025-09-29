import { test, expect } from '@playwright/test';

const viewerUrl = process.env.VIEWER_URL;

if (!viewerUrl) {
  test.describe('viewer baseline', () => {
    test('skipped because VIEWER_URL not set', async () => {
      test.skip(true, 'VIEWER_URL env var must be provided');
    });
  });
} else {
  test.describe('viewer baseline', () => {
    test('loads core UI elements and toggles details drawer', async ({ page }) => {
      await page.goto(viewerUrl, { waitUntil: 'domcontentloaded' });

      await page.waitForSelector('canvas', { timeout: 15_000 });
      const canvasCount = await page.locator('canvas').count();
      expect(canvasCount).toBeGreaterThan(0);

      const menuContainer = page.locator('#menuContainer');
      await expect(menuContainer).toBeVisible();

      const detailsButton = page.locator('#detailsButton');
      await expect(detailsButton).toBeVisible();

      await detailsButton.click();
      const detailsBox = page.locator('#detailsBox');
      await expect(detailsBox).toHaveClass(/show/);

      const compassIcon = page.locator('#compassIcon');
      await expect(compassIcon).toBeVisible();

      const overlay = page.locator('#overlay-ui');
      await expect(overlay).toBeVisible();

      await detailsButton.click();
      await expect(detailsBox).not.toHaveClass(/show/);
    });
  });
}
