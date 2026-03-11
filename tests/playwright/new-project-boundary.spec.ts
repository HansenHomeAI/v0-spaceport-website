import { expect, test } from '@playwright/test';

const email = process.env.TEST_EMAIL;
const password = process.env.TEST_PASSWORD;
const previewUrl = process.env.PREVIEW_URL;

const requireEnv = () => {
  if (!email || !password || !previewUrl) {
    test.skip(true, 'PREVIEW_URL, TEST_EMAIL, and TEST_PASSWORD must be set');
  }
};

const dragLocatorBy = async (
  page: import('@playwright/test').Page,
  selector: string,
  deltaX: number,
  deltaY: number
) => {
  const box = await page.locator(selector).boundingBox();
  if (!box) {
    throw new Error(`Could not find draggable element: ${selector}`);
  }

  const startX = box.x + box.width / 2;
  const startY = box.y + box.height / 2;
  await page.mouse.move(startX, startY);
  await page.mouse.down();
  await page.mouse.move(startX + deltaX, startY + deltaY, { steps: 12 });
  await page.mouse.up();
};

const locatorCenter = async (
  locator: import('@playwright/test').Locator
): Promise<{ x: number; y: number }> => {
  const box = await locator.boundingBox();
  if (!box) {
    throw new Error('Could not resolve locator bounding box');
  }
  return { x: box.x + box.width / 2, y: box.y + box.height / 2 };
};

test('fullscreen boundary editor applies a boundary-aware mission', async ({ page }) => {
  requireEnv();

  const optimizeBoundaryPayloads: any[] = [];
  const batteryCsvPayloads: any[] = [];
  const projectSavePayloads: any[] = [];

  page.on('request', (request) => {
    const method = request.method();
    if (request.url().includes('/api/optimize-boundary') && method === 'POST') {
      optimizeBoundaryPayloads.push(request.postDataJSON());
    }
    if (request.url().includes('/api/csv/battery/') && method === 'POST') {
      batteryCsvPayloads.push(request.postDataJSON());
    }
    if (request.url().includes('/projects') && (method === 'POST' || method === 'PATCH')) {
      projectSavePayloads.push(request.postDataJSON());
    }
  });

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
    await newPasswordInput.fill(`Boundary${suffix}Aa!`);
    await page.getByPlaceholder(/handle/i).fill(`boundary${Date.now()}`);
    await saveAndSignIn.click();
    await expect(saveAndSignIn).not.toBeVisible({ timeout: 20_000 });
  }

  await expect(page.getByText('New Project')).toBeVisible({ timeout: 20_000 });
  await page.locator('.new-project-card').click();
  await expect(page.locator('#newProjectPopup')).toBeVisible();

  await page.locator('#address-search').fill('39.739200, -104.990300');
  await page.locator('#address-search').press('Enter');
  await page.getByPlaceholder('Duration').fill('20');
  await page.getByPlaceholder('Quantity').fill('3');

  await page.click('#expand-button');
  await expect(page.locator('.map-wrapper.fullscreen')).toBeVisible();

  await page.getByRole('button', { name: 'Boundary' }).click();
  await expect(page.locator('.boundary-editor-bar')).toBeVisible();
  await expect(page.locator('.boundary-handle-marker.center')).toBeVisible();
  await expect(page.locator('.battery-view-btn.active')).toHaveCount(3);

  await dragLocatorBy(page, '.boundary-handle-marker.major', 90, -25);
  await dragLocatorBy(page, '.boundary-handle-marker.minor', 0, 55);

  await page.getByRole('button', { name: 'Apply' }).click();
  await expect.poll(() => optimizeBoundaryPayloads.length, { timeout: 20_000 }).toBeGreaterThan(0);
  expect(optimizeBoundaryPayloads[0]?.boundary).toBeTruthy();

  const batteryPayloadCheckpoint = batteryCsvPayloads.length;
  await page.getByRole('button', { name: /^Battery 1$/ }).first().click();
  await expect
    .poll(() => batteryCsvPayloads.slice(batteryPayloadCheckpoint).find((payload) => payload?.boundary && payload?.boundaryPlan), {
      timeout: 20_000,
    })
    .toBeTruthy();
  const boundaryBatteryPayload = batteryCsvPayloads
    .slice(batteryPayloadCheckpoint)
    .find((payload) => payload?.boundary && payload?.boundaryPlan);
  expect(boundaryBatteryPayload?.boundary).toBeTruthy();
  expect(boundaryBatteryPayload?.boundaryPlan).toBeTruthy();

  const batteryOneMarkers = page.locator('.waypoint-marker[data-battery-index="1"]');
  const markerBeforeInsert = await batteryOneMarkers.count();
  expect(markerBeforeInsert).toBeGreaterThan(3);

  const firstMarker = batteryOneMarkers.nth(0);
  const secondMarker = batteryOneMarkers.nth(1);
  const originalFirstCenter = await locatorCenter(firstMarker);
  await dragLocatorBy(page, '.waypoint-marker[data-battery-index="1"]', 45, -20);
  await expect.poll(
    () => projectSavePayloads.some((payload) => payload?.params?.waypointOverrides?.batteries?.['1']),
    { timeout: 20_000 }
  ).toBeTruthy();
  const movedFirstCenter = await locatorCenter(firstMarker);
  expect(Math.hypot(movedFirstCenter.x - originalFirstCenter.x, movedFirstCenter.y - originalFirstCenter.y)).toBeGreaterThan(10);

  await page.getByPlaceholder('Min Distance').fill('300');
  await page.waitForTimeout(1_500);
  const persistedFirstCenter = await locatorCenter(firstMarker);
  expect(Math.hypot(persistedFirstCenter.x - movedFirstCenter.x, persistedFirstCenter.y - movedFirstCenter.y)).toBeLessThan(18);

  const firstCenter = await locatorCenter(firstMarker);
  const secondCenter = await locatorCenter(secondMarker);

  await page.mouse.move((firstCenter.x + secondCenter.x) / 2, (firstCenter.y + secondCenter.y) / 2);
  await expect(page.locator('.waypoint-insert-marker')).toBeVisible({ timeout: 10_000 });
  await page.locator('.waypoint-insert-marker').click();
  await expect(batteryOneMarkers).toHaveCount(markerBeforeInsert + 1);

  const draggedMarkerCenter = await locatorCenter(firstMarker);
  const targetMarkerCenter = await locatorCenter(secondMarker);
  await page.mouse.move(draggedMarkerCenter.x, draggedMarkerCenter.y);
  await page.mouse.down();
  await page.mouse.move(targetMarkerCenter.x, targetMarkerCenter.y, { steps: 24 });
  await page.waitForTimeout(700);
  await page.mouse.up();
  await expect(batteryOneMarkers).toHaveCount(markerBeforeInsert);
});
