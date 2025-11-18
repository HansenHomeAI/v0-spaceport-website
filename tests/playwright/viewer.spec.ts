// NOTE: tests/ has its own vendored node_modules, so reference the workspace-level package directly.
import { test, expect } from '../../node_modules/@playwright/test';

const SAMPLE_BUNDLE = 'https://spaceport-ml-processing.s3.us-west-2.amazonaws.com/public-viewer/sogs-test-1753999934/';

test.describe('Gaussian Viewer', () => {
  test('loads public sample bundle and reports stats', async ({ page }) => {
    const encoded = encodeURIComponent(SAMPLE_BUNDLE);
    await page.goto(`/viewer.html?bundle=${encoded}`);

    await expect(page.locator('#statusMessage')).toContainText('Loaded', { timeout: 30_000 });
    await expect(page.locator('#statSplats')).not.toHaveText('0');
    await expect(page.locator('#statRendered')).not.toHaveText('0');
    await expect(page.locator('#viewerCanvas')).toBeVisible();
  });
});
