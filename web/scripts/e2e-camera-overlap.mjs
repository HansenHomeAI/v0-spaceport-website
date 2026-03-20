/**
 * E2E smoke test for /camera-overlap (requires server: npm run start -- -p 3456)
 * Run: BASE_URL=http://127.0.0.1:3456 node scripts/e2e-camera-overlap.mjs
 */
import { chromium } from 'playwright';
import assert from 'node:assert/strict';

const BASE = process.env.BASE_URL || 'http://127.0.0.1:3000';

async function main() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  await page.goto(`${BASE}/camera-overlap`, { waitUntil: 'domcontentloaded', timeout: 60_000 });
  await page.getByRole('heading', { name: 'Drone Path Spacing' }).waitFor({ timeout: 15_000 });

  const switchBtn = page.getByTestId('capture-ring-switch');
  await assert.equal(await switchBtn.getAttribute('aria-checked'), 'true');

  const pctBefore = await page.getByTestId('capture-pct-text').textContent();
  assert.ok(pctBefore && /^\d+%$/.test(pctBefore.trim()), `unexpected pct: ${pctBefore}`);

  await switchBtn.click();
  await assert.equal(await switchBtn.getAttribute('aria-checked'), 'false');
  await assert.equal((await page.getByTestId('capture-pct-text').textContent())?.trim(), '100%');

  await switchBtn.click();
  await assert.equal(await switchBtn.getAttribute('aria-checked'), 'true');

  await page.getByTestId('height-slider').evaluate((el) => {
    el.value = '400';
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
  });

  const footnote = await page.getByText(/hypotenuse/).first().textContent();
  assert.ok(footnote && /hypotenuse\s+[\d.]+/.test(footnote), `footnote missing hypotenuse value: ${footnote}`);

  await browser.close();
  console.log('e2e-camera-overlap.mjs: passed');
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
