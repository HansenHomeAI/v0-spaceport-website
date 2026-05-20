/**
 * Render a single MD1 viewer camera pose for side-by-side input comparisons.
 *
 * Usage:
 *   cd web
 *   MD1_VIEWER_URL=https://... \
 *   MD1_BUNDLE_URL=https://.../meta.json \
 *   MD1_CAM_POS="x,y,z" \
 *   MD1_CAM_TARGET="x,y,z" \
 *   MD1_CAM_UP="x,y,z" \
 *   MD1_SKYBOX="background_skybox.webp" \
 *   MD1_OUT="../logs/md1-camera-check.png" \
 *   node scripts/render-md1-camera-check.mjs
 */

import { chromium } from "playwright";
import fs from "node:fs/promises";
import path from "node:path";

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function parseVector(value) {
  const parts = String(value ?? "")
    .split(",")
    .map((entry) => Number.parseFloat(entry.trim()));
  if (parts.length !== 3 || !parts.every(Number.isFinite)) {
    return null;
  }
  return parts;
}

async function waitForFirstFrame(page) {
  await page.locator('[data-testid="md1-bundle-metrics"]').waitFor({ state: "attached", timeout: 120000 });
  const start = Date.now();
  let lastMetrics = null;
  while (Date.now() - start < 180000) {
    const dataset = await page
      .locator('[data-testid="md1-bundle-metrics"]')
      .evaluate((element) => ({ ...element.dataset }))
      .catch(() => null);
    lastMetrics = dataset;

    const frame = page.frames().find((candidate) => candidate.url().includes("/supersplat-lod-viewer/index.html"));
    const frameReady = await frame
      ?.evaluate(() => ({
        readyState: document.readyState,
        hasContext: !!window.__sogsCtx?.app,
        hasGsplat: !!window.__sogsCtx?.app?.root?.findByName?.("gsplat"),
      }))
      .catch(() => null);

    if (frameReady?.hasContext && frameReady?.hasGsplat) {
      return { dataset, frameReady };
    }

    await page.waitForTimeout(1000);
  }
  throw new Error(`timed out waiting for md1-viewer; lastMetrics=${JSON.stringify(lastMetrics)}`);
}

function isRetryableScreenshotError(error) {
  const message = String(error?.message ?? error ?? "");
  return (
    message.includes("Element is not attached to the DOM") ||
    message.includes("Execution context was destroyed") ||
    message.includes("Target closed") ||
    message.includes("Navigation interrupted the execution") ||
    message.includes("has been closed")
  );
}

async function screenshotIframeStable(page, outPath) {
  let lastError = null;
  for (let attempt = 1; attempt <= 4; attempt += 1) {
    const iframe = page.locator("iframe.md1-frame");
    try {
      await iframe.waitFor({ state: "visible", timeout: 60000 });
      await iframe.screenshot({ path: outPath });
      return;
    } catch (error) {
      lastError = error;
      if (!isRetryableScreenshotError(error)) throw error;
      await page.waitForTimeout(500 * attempt);
    }
  }

  try {
    await page.screenshot({ path: outPath, fullPage: false });
    return;
  } catch (error) {
    throw lastError ?? error;
  }
}

const baseUrl = (process.env.MD1_VIEWER_URL ?? "").replace(/\/$/, "");
const bundleUrl = process.env.MD1_BUNDLE_URL ?? "";
const camPos = parseVector(process.env.MD1_CAM_POS);
const camTarget = parseVector(process.env.MD1_CAM_TARGET);
const camUp = parseVector(process.env.MD1_CAM_UP);
const skybox = (process.env.MD1_SKYBOX ?? "").trim();
const sceneScale = (process.env.MD1_SCENE_SCALE ?? "").trim();
const flipY = ["1", "true", "yes", "on"].includes((process.env.MD1_FLIP_Y ?? "").trim().toLowerCase());
const collapsePanel = ["1", "true", "yes", "on"].includes(
  (process.env.MD1_COLLAPSE_PANEL ?? "").trim().toLowerCase(),
);
const screenshotTarget = (process.env.MD1_SCREENSHOT_TARGET ?? "").trim().toLowerCase();
const outPath = process.env.MD1_OUT ?? "";

assert(baseUrl, "MD1_VIEWER_URL is required");
assert(bundleUrl, "MD1_BUNDLE_URL is required");
assert(camPos, "MD1_CAM_POS must be x,y,z");
assert(camTarget, "MD1_CAM_TARGET must be x,y,z");
assert(outPath, "MD1_OUT is required");

await fs.mkdir(path.dirname(outPath), { recursive: true });

const params = new URLSearchParams({
  url: bundleUrl,
  camPos: camPos.join(","),
  camTarget: camTarget.join(","),
});
if (camUp) {
  params.set("camUp", camUp.join(","));
}
if (skybox) {
  params.set("skybox", skybox);
}
if (sceneScale) {
  params.set("sceneScale", sceneScale);
} else if (flipY) {
  params.set("flipY", "1");
}
if (collapsePanel) {
  params.set("panel", "collapsed");
}

const url = `${baseUrl}/md1-viewer?${params.toString()}`;
const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 960 } });
  await page.goto(url, { waitUntil: "domcontentloaded", timeout: 120000 });
  const metrics = await waitForFirstFrame(page);
  await page.waitForTimeout(1200);
  if (screenshotTarget === "iframe") {
    await screenshotIframeStable(page, outPath);
  } else {
    await page.screenshot({ path: outPath, fullPage: false });
  }
  console.log(`OK ${outPath}`);
  console.log(`metrics ${JSON.stringify(metrics)}`);
} finally {
  await browser.close();
}
