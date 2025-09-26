import path from 'path';
import { fileURLToPath } from 'url';
import { test, expect } from '@playwright/test';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const sampleCsvPath = path.resolve(__dirname, 'fixtures/sample-flight.csv');

const basePath = '/dev/flight-viewer';

test.describe('Flight viewer', () => {
  test('parses CSV and surfaces mission metrics', async ({ page }) => {
    await page.goto(basePath, { waitUntil: 'networkidle' });

    await expect(page.locator('h1')).toContainText('Flight Path 3D');

    await page.setInputFiles('#flightPathCsv', sampleCsvPath);

    await expect(page.getByRole('heading', { name: 'Flight Metrics' })).toBeVisible();
    await expect(page.getByTestId('metric-horizontal-distance')).toContainText('Horizontal Distance');
    await expect(page.getByTestId('metric-altitude-range')).toContainText('Altitude Range');
    await expect(page.getByTestId('metric-waypoints')).toContainText('4');

    await expect(page.getByRole('row', { name: /38\.27371/ })).toBeVisible();
  });
});
