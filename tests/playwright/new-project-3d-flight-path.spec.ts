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

async function readMapPitch(page: import('@playwright/test').Page): Promise<number> {
  const value = await page.locator('.map-wrapper').getAttribute('data-map-pitch');
  return Number.parseFloat(value ?? '0');
}

async function readAltitudeRange(page: import('@playwright/test').Page): Promise<number> {
  const value = await page.locator('.map-wrapper').getAttribute('data-altitude-range-feet');
  return Number.parseFloat(value ?? '0');
}

async function readRenderedPathPointCount(page: import('@playwright/test').Page): Promise<number> {
  const value = await page.locator('.map-wrapper').getAttribute('data-rendered-path-point-count');
  return Number.parseFloat(value ?? '0');
}

async function readElevatedLineCount(page: import('@playwright/test').Page): Promise<number> {
  const value = await page.locator('.map-wrapper').getAttribute('data-elevated-line-count');
  return Number.parseFloat(value ?? '0');
}

test('new project modal renders altitude in the live map and restores camera after boundary mode', async ({ page }) => {
  requireEnv();

  await loginAndOpenNewProjectModal(page);

  await page.locator('#address-search').fill('39.739200, -104.990300');
  await page.locator('#address-search').press('Enter');
  await page.getByPlaceholder('Duration').fill('20');
  await page.getByPlaceholder('Quantity').fill('2');
  await page.getByPlaceholder('Minimum').fill('120');
  await page.getByPlaceholder('Maximum').fill('360');
  await page.locator('.capture-mode-toggle').click();

  await page.locator('.battery-view-btn').first().click();
  await expect(page.locator('.battery-view-btn.active')).toHaveCount(1, { timeout: 30_000 });
  await expect(page.getByRole('button', { name: '3D' })).toHaveCount(0);
  await page.locator('#expand-button').click();

  await expect(page.locator('.map-camera-hint')).toBeVisible();
  await expect(page.locator('.waypoint-marker')).toHaveCount(1, { timeout: 1_000 }).catch(() => {});
  await page.waitForFunction(() => {
    const markers = Array.from(document.querySelectorAll<HTMLElement>('.waypoint-marker[data-altitude-feet]'));
    return markers.length > 2;
  }, undefined, { timeout: 30_000 });
  await page.waitForFunction(() => {
    const wrapper = document.querySelector('.map-wrapper');
    const renderedPointCount = Number.parseFloat(wrapper?.getAttribute('data-rendered-path-point-count') ?? '0');
    const markerCount = document.querySelectorAll('.waypoint-marker[data-altitude-feet]').length;
    return renderedPointCount > markerCount;
  }, undefined, { timeout: 30_000 });
  await page.waitForFunction(() => {
    const wrapper = document.querySelector('.map-wrapper');
    return Number.parseFloat(wrapper?.getAttribute('data-elevated-line-count') ?? '0') > 0;
  }, undefined, { timeout: 30_000 });

  const altitudeRangeFeet = await readAltitudeRange(page);
  expect(altitudeRangeFeet).toBeGreaterThan(100);
  expect(await readElevatedLineCount(page)).toBeGreaterThan(0);
  expect(await readRenderedPathPointCount(page)).toBeGreaterThan(
    await page.locator('.waypoint-marker[data-altitude-feet]').count(),
  );

  const markerMetricsBeforePitch = await page.locator('.waypoint-marker').evaluateAll((elements) => {
    return elements.map((element) => {
      const rect = element.getBoundingClientRect();
      return {
        batteryIndex: Number.parseInt(element.dataset.batteryIndex ?? '-1', 10),
        waypointIndex: Number.parseInt(element.dataset.waypointIndex ?? '-1', 10),
        altitudeFeet: Number.parseFloat(element.dataset.altitudeFeet ?? '0'),
        curveFeet: Number.parseFloat(element.dataset.curveFeet ?? '0'),
        top: rect.top,
      };
    });
  });
  const markerAltitudes = markerMetricsBeforePitch.map((marker) => marker.altitudeFeet);
  expect(Math.max(...markerAltitudes) - Math.min(...markerAltitudes)).toBeGreaterThan(100);
  const markerCurves = markerMetricsBeforePitch.map((marker) => marker.curveFeet);
  expect(Math.max(...markerCurves)).toBeGreaterThan(0);

  const canvas = page.locator('.mapboxgl-canvas');
  await expect(canvas).toBeVisible();
  const bounds = await canvas.boundingBox();
  expect(bounds).not.toBeNull();
  if (!bounds) {
    throw new Error('Expected map canvas bounds');
  }

  const centerX = bounds.x + bounds.width / 2;
  const centerY = bounds.y + bounds.height / 2;
  expect(await readMapPitch(page)).toBeLessThan(1);
  await page.evaluate(() => {
    const canvas = document.querySelector('.mapboxgl-canvas');
    if (!(canvas instanceof HTMLElement)) {
      throw new Error('Mapbox canvas not found');
    }
    canvas.focus();
  });
  await page.mouse.move(centerX, centerY);
  for (let step = 0; step < 8; step += 1) {
    await page.keyboard.press('Shift+ArrowUp');
    await page.waitForTimeout(200);
  }

  await page.waitForFunction(() => {
    const wrapper = document.querySelector('.map-wrapper');
    const pitch = Number.parseFloat(wrapper?.getAttribute('data-map-pitch') ?? '0');
    return pitch > 5;
  }, undefined, { timeout: 10_000 });
  const pitchedMapDegrees = await readMapPitch(page);
  expect(pitchedMapDegrees).toBeGreaterThan(5);

  const markerMetricsAfterPitch = await page.locator('.waypoint-marker').evaluateAll((elements) => {
    return elements.map((element) => {
      const rect = element.getBoundingClientRect();
      return {
        batteryIndex: Number.parseInt(element.dataset.batteryIndex ?? '-1', 10),
        waypointIndex: Number.parseInt(element.dataset.waypointIndex ?? '-1', 10),
        altitudeFeet: Number.parseFloat(element.dataset.altitudeFeet ?? '0'),
        top: rect.top,
      };
    });
  });
  const highestMarkerBeforePitch = markerMetricsBeforePitch.reduce((best, current) => (
    current.altitudeFeet > best.altitudeFeet ? current : best
  ));
  const lowestMarkerBeforePitch = markerMetricsBeforePitch.reduce((best, current) => (
    current.altitudeFeet < best.altitudeFeet ? current : best
  ));
  const highestMarkerAfterPitch = markerMetricsAfterPitch.find((marker) => (
    marker.batteryIndex === highestMarkerBeforePitch.batteryIndex
      && marker.waypointIndex === highestMarkerBeforePitch.waypointIndex
  ));
  const lowestMarkerAfterPitch = markerMetricsAfterPitch.find((marker) => (
    marker.batteryIndex === lowestMarkerBeforePitch.batteryIndex
      && marker.waypointIndex === lowestMarkerBeforePitch.waypointIndex
  ));
  expect(highestMarkerAfterPitch).toBeDefined();
  expect(lowestMarkerAfterPitch).toBeDefined();
  const separationBeforePitch = Math.abs(highestMarkerBeforePitch.top - lowestMarkerBeforePitch.top);
  const separationAfterPitch = Math.abs(
    highestMarkerAfterPitch!.top - lowestMarkerAfterPitch!.top,
  );
  expect(separationAfterPitch).toBeGreaterThan(separationBeforePitch + 2);

  await page.getByRole('button', { name: 'Boundary' }).click();
  await expect(page.locator('.boundary-editor-bar')).toBeVisible({ timeout: 30_000 });
  await page.waitForFunction(() => {
    const wrapper = document.querySelector('.map-wrapper');
    const pitch = Number.parseFloat(wrapper?.getAttribute('data-map-pitch') ?? '0');
    return pitch < 1;
  }, undefined, { timeout: 10_000 });

  await page.getByRole('button', { name: 'Cancel' }).click();
  await page.waitForFunction(() => {
    const wrapper = document.querySelector('.map-wrapper');
    const pitch = Number.parseFloat(wrapper?.getAttribute('data-map-pitch') ?? '0');
    return pitch > 5;
  }, undefined, { timeout: 10_000 });
  expect(await readMapPitch(page)).toBeGreaterThan(5);
});
