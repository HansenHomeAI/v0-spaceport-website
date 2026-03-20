import { test, expect } from '@playwright/test';

test.describe('Camera Overlap 3D page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/camera-overlap');
    await page.waitForLoadState('networkidle');
  });

  test('renders the Three.js canvas', async ({ page }) => {
    const container = page.locator('[data-testid="three-view-container"]');
    await expect(container).toBeVisible({ timeout: 10_000 });

    const canvas = container.locator('canvas');
    await expect(canvas).toBeVisible({ timeout: 10_000 });
  });

  test('shows overlap HUD bottom-left with IoU and spacing', async ({ page }) => {
    const hud = page.locator('[data-testid="three-view-hud"]');
    await expect(hud).toBeVisible();
    await expect(page.locator('[data-testid="overlap-hud-primary"]')).toContainText('Overlap:');
    await expect(page.locator('[data-testid="overlap-hud-primary"]')).toContainText('%');
    await expect(page.locator('[data-testid="overlap-hud-meta"]')).toContainText('ft apart');
    await expect(page.locator('[data-testid="overlap-hud-meta"]')).toContainText('AGL');
  });

  test('height slider changes overlap percentage', async ({ page }) => {
    const primary = page.locator('[data-testid="overlap-hud-primary"]');
    const meta = page.locator('[data-testid="overlap-hud-meta"]');
    await expect(primary).toBeVisible();
    const initialMeta = await meta.textContent();

    const slider = page.locator('[data-testid="height-slider"]');
    await slider.fill('50');
    await slider.dispatchEvent('input');

    await expect(async () => {
      const newMeta = await meta.textContent();
      expect(newMeta).not.toBe(initialMeta);
    }).toPass({ timeout: 5000 });
  });

  test('speed slider changes overlap percentage', async ({ page }) => {
    const primary = page.locator('[data-testid="overlap-hud-primary"]');
    await expect(primary).toBeVisible();
    const initialText = await primary.textContent();

    const slider = page.locator('[data-testid="speed-slider"]');
    await slider.fill('15');
    await slider.dispatchEvent('input');

    await expect(async () => {
      const newText = await primary.textContent();
      expect(newText).not.toBe(initialText);
    }).toPass({ timeout: 5000 });
  });

  test('displays FOV label with overlap percent', async ({ page }) => {
    const label = page.locator('[data-testid="camera-overlap-page-label"]');
    await expect(label).toContainText('77°×55° FOV');
    await expect(label).toContainText('% overlap');
  });

  test('displays speed slider', async ({ page }) => {
    const slider = page.locator('[data-testid="speed-slider"]');
    await expect(slider).toBeVisible();
  });

  test('footnote shows gimbal angle and spacing', async ({ page }) => {
    const footnote = page.locator('p:has-text("gimbal")');
    await expect(footnote).toBeVisible();
    await expect(footnote).toContainText('hyp');
    await expect(footnote).toContainText('spacing');
  });
});
