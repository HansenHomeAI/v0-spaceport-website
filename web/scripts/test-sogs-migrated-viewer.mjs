/**
 * Smoke test for /sogs-migrated-viewer: standalone chrome, iframe, first frame, bridge ready.
 *
 * Usage (from web/):
 *   SOGS_MIGRATED_URL=http://127.0.0.1:3000 node scripts/test-sogs-migrated-viewer.mjs
 */

import { chromium } from "playwright";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, "..", "..");
const logsDir = path.join(repoRoot, "logs");

const baseUrl = (process.env.SOGS_MIGRATED_URL ?? "http://127.0.0.1:3000").replace(/\/$/, "");
const bundleUrl =
  process.env.SOGS_BUNDLE_URL ??
  "https://spaceport-ml-processing.s3.amazonaws.com/compressed/sogs-test-1763664401/supersplat_bundle/meta.json";

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

(async () => {
  await fs.mkdir(logsDir, { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });

  const encoded = encodeURIComponent(bundleUrl);
  await page.goto(`${baseUrl}/sogs-migrated-viewer?url=${encoded}`, {
    waitUntil: "domcontentloaded",
    timeout: 120000,
  });

  assert((await page.locator("header").count()) === 0, "no site header on standalone migrated viewer");
  await page.waitForSelector('iframe[title="sogs-migrated-viewer"]', { timeout: 60000 });

  const splatFrame = page.frames().find((f) => f.url().includes("supersplat-viewer"));
  assert(!!splatFrame, "supersplat iframe frame exists");
  await page.waitForTimeout(3000);
  const xzReady = await splatFrame.evaluate(() => window.__sogsSplatXzDragReady === true);
  assert(xzReady, "sogs-bridge sets __sogsSplatXzDragReady");

  const shot = path.join(logsDir, "sogs-migrated-viewer-smoke.png");
  await page.screenshot({ path: shot, fullPage: true });
  console.log(`OK — screenshot ${shot}`);
  await browser.close();
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
