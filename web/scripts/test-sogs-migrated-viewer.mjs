/**
 * Deep regression for /sogs-migrated-viewer.
 *
 * Validates:
 * - default Canyon preset still loads with scene tools
 * - latest SfM, 3DGS, and compressed S3 artifacts load through the same pasted-URL UX
 * - rendered pixels are visible for each stage
 * - camera can orbit and zoom for each stage
 *
 * Usage (from web/):
 *   SOGS_MIGRATED_URL=http://127.0.0.1:3000 node scripts/test-sogs-migrated-viewer.mjs
 */

import { chromium } from "playwright";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import zlib from "node:zlib";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, "..", "..");
const logsDir = path.join(repoRoot, "logs");
const LOAD_TIMEOUT_MS = 360000;

const baseUrl = (process.env.SOGS_MIGRATED_URL ?? "http://127.0.0.1:3000").replace(/\/$/, "");
const DEFAULT_PRESET_URL =
  process.env.SOGS_DEFAULT_URL ??
  "https://spaceport-ml-processing.s3.amazonaws.com/compressed/sogs-test-1763664401/supersplat_bundle/meta.json";
const LATEST_COMPRESSED_URL =
  process.env.SOGS_COMPRESSED_URL ??
  "https://spaceport-ml-processing.s3.amazonaws.com/compressed/manual-3dgs-1774642514/supersplat_bundle/meta.json";
const LATEST_3DGS_URL =
  process.env.SOGS_3DGS_URL ??
  "https://spaceport-ml-processing.s3.amazonaws.com/3dgs/manual-3dgs-1774642514/ml-job-20260327-201514-manual-3-3dgs/output/model.tar.gz";
const LATEST_SFM_URL =
  process.env.SOGS_SFM_URL ??
  "https://spaceport-ml-processing.s3.amazonaws.com/colmap/colmap-gpu-subset-runtime2-1774553792/";

const CASES = [
  {
    name: "default-canyon",
    queryUrl: null,
    inputUrl: DEFAULT_PRESET_URL,
    expectedStage: "Compressed SOGS bundle",
    expectCanyonTools: true,
    verifyNavigation: false,
    minBright: 5000,
  },
  {
    name: "compressed-latest",
    queryUrl: LATEST_COMPRESSED_URL,
    inputUrl: LATEST_COMPRESSED_URL,
    expectedStage: "Compressed SOGS bundle",
    expectCanyonTools: false,
    verifyNavigation: true,
    minBright: 5000,
  },
  {
    name: "3dgs-latest",
    queryUrl: LATEST_3DGS_URL,
    inputUrl: LATEST_3DGS_URL,
    expectedStage: "3DGS model",
    expectCanyonTools: false,
    verifyNavigation: true,
    minBright: 5000,
  },
  {
    name: "sfm-latest",
    queryUrl: LATEST_SFM_URL,
    inputUrl: LATEST_SFM_URL,
    expectedStage: "SfM sparse point cloud",
    expectCanyonTools: false,
    verifyNavigation: true,
    minBright: 400,
  },
];

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function paethPredictor(a, b, c) {
  const p = a + b - c;
  const pa = Math.abs(p - a);
  const pb = Math.abs(p - b);
  const pc = Math.abs(p - c);
  if (pa <= pb && pa <= pc) return a;
  if (pb <= pc) return b;
  return c;
}

function decodePngRgba(buffer) {
  const signature = "89504e470d0a1a0a";
  if (buffer.subarray(0, 8).toString("hex") !== signature) {
    throw new Error("expected PNG screenshot");
  }

  let offset = 8;
  let width = 0;
  let height = 0;
  let bitDepth = 0;
  let colorType = 0;
  const idatParts = [];

  while (offset < buffer.length) {
    const length = buffer.readUInt32BE(offset);
    offset += 4;
    const type = buffer.subarray(offset, offset + 4).toString("ascii");
    offset += 4;
    const data = buffer.subarray(offset, offset + length);
    offset += length;
    offset += 4;

    if (type === "IHDR") {
      width = data.readUInt32BE(0);
      height = data.readUInt32BE(4);
      bitDepth = data[8];
      colorType = data[9];
    } else if (type === "IDAT") {
      idatParts.push(data);
    } else if (type === "IEND") {
      break;
    }
  }

  if (bitDepth !== 8 || ![2, 6].includes(colorType)) {
    throw new Error(`unsupported PNG format bitDepth=${bitDepth} colorType=${colorType}`);
  }

  const sourceBytesPerPixel = colorType === 6 ? 4 : 3;
  const stride = width * sourceBytesPerPixel;
  const inflated = zlib.inflateSync(Buffer.concat(idatParts));
  const decoded = Buffer.alloc(width * height * sourceBytesPerPixel);

  let srcOffset = 0;
  let dstOffset = 0;
  for (let y = 0; y < height; y += 1) {
    const filter = inflated[srcOffset];
    srcOffset += 1;
    for (let x = 0; x < stride; x += 1) {
      const raw = inflated[srcOffset];
      srcOffset += 1;
      const left = x >= sourceBytesPerPixel ? decoded[dstOffset - sourceBytesPerPixel] : 0;
      const up = y > 0 ? decoded[dstOffset - stride] : 0;
      const upLeft = y > 0 && x >= sourceBytesPerPixel ? decoded[dstOffset - stride - sourceBytesPerPixel] : 0;
      let value = raw;
      if (filter === 1) value = (raw + left) & 0xff;
      else if (filter === 2) value = (raw + up) & 0xff;
      else if (filter === 3) value = (raw + Math.floor((left + up) / 2)) & 0xff;
      else if (filter === 4) value = (raw + paethPredictor(left, up, upLeft)) & 0xff;
      decoded[dstOffset] = value;
      dstOffset += 1;
    }
  }

  if (colorType === 6) {
    return { width, height, pixels: decoded };
  }

  const pixels = Buffer.alloc(width * height * 4);
  for (let src = 0, dst = 0; src < decoded.length; src += 3, dst += 4) {
    pixels[dst] = decoded[src];
    pixels[dst + 1] = decoded[src + 1];
    pixels[dst + 2] = decoded[src + 2];
    pixels[dst + 3] = 255;
  }

  return { width, height, pixels };
}

function summarizeRenderedPixels(buffer) {
  const { width, height, pixels } = decodePngRgba(buffer);
  let bright = 0;
  for (let i = 0; i < pixels.length; i += 4) {
    if (pixels[i] + pixels[i + 1] + pixels[i + 2] > 36) bright += 1;
  }
  return { width, height, bright };
}

async function readCamera(frame) {
  return frame.evaluate(() => {
    const cam = window.__sogsCtx?.viewer?.cameraManager?.camera;
    return cam
      ? {
          position: { x: cam.position.x, y: cam.position.y, z: cam.position.z },
          angles: { x: cam.angles.x, y: cam.angles.y, z: cam.angles.z },
          distance: cam.distance,
        }
      : null;
  });
}

function cameraDelta(a, b) {
  if (!a || !b) return 0;
  return Math.max(
    Math.abs(a.position.x - b.position.x),
    Math.abs(a.position.y - b.position.y),
    Math.abs(a.position.z - b.position.z),
    Math.abs(a.angles.x - b.angles.x),
    Math.abs(a.angles.y - b.angles.y),
    Math.abs(a.angles.z - b.angles.z),
    Math.abs((a.distance ?? 0) - (b.distance ?? 0)),
  );
}

async function loadCase(page, testCase) {
  const destination = testCase.queryUrl
    ? `${baseUrl}/sogs-migrated-viewer?url=${encodeURIComponent(testCase.queryUrl)}`
    : `${baseUrl}/sogs-migrated-viewer`;

  await page.goto(destination, { waitUntil: "domcontentloaded", timeout: LOAD_TIMEOUT_MS });
  assert((await page.locator("header").count()) === 0, "no site header on standalone migrated viewer");
  await page.waitForSelector('iframe[title="sogs-migrated-viewer"]', { timeout: LOAD_TIMEOUT_MS });
  await page.locator("#sogs-migrated-url").waitFor({ state: "visible", timeout: LOAD_TIMEOUT_MS });
  assert((await page.locator("#sogs-migrated-url").inputValue()) === testCase.inputUrl, "pipeline URL should populate");
  await page.getByText(`Detected: ${testCase.expectedStage}`).waitFor({ state: "visible", timeout: LOAD_TIMEOUT_MS });

  const frameSrc = await page.locator('iframe[title="sogs-migrated-viewer"]').evaluate((node) => node.getAttribute("src"));
  const decodedFrameSrc = frameSrc ? decodeURIComponent(frameSrc) : "";
  assert(frameSrc && frameSrc.includes("content="), "viewer iframe should include content query");
  assert(decodedFrameSrc.includes("/api/sogs-proxy/"), "viewer iframe should load through stage-aware API route");

  const splatFrame = page.frames().find((frame) => frame.url().includes("supersplat-viewer"));
  assert(!!splatFrame, "supersplat iframe frame exists");

  await splatFrame.waitForFunction(() => !!document.querySelector("canvas"), null, { timeout: LOAD_TIMEOUT_MS });
  await splatFrame.waitForFunction(() => {
    const cam = window.__sogsCtx?.viewer?.cameraManager?.camera;
    return !!cam && [cam.position.x, cam.position.y, cam.position.z, cam.distance].every(Number.isFinite);
  }, null, { timeout: LOAD_TIMEOUT_MS });

  if (testCase.expectCanyonTools) {
    await page.getByTestId("sogs-hole-picker").waitFor({ state: "visible", timeout: 10000 });
    await page.getByTestId("focus-scene-center").waitFor({ state: "visible", timeout: 10000 });
  } else {
    assert((await page.getByTestId("sogs-hole-picker").count()) === 0, "generic stage should hide hole picker");
    assert((await page.getByTestId("focus-scene-center").count()) === 0, "generic stage should hide canyon focus button");
  }

  const renderBuffer = await page.locator('iframe[title="sogs-migrated-viewer"]').screenshot();
  const renderStats = summarizeRenderedPixels(renderBuffer);
  assert(
    renderStats.bright > testCase.minBright,
    `${testCase.name} should render visible pixels, got ${JSON.stringify(renderStats)}`,
  );

  return { splatFrame, renderStats };
}

async function verifyNavigation(page, frame, testCase) {
  if (testCase.expectCanyonTools) {
    const autoRotateToggle = page.getByLabel("Toggle auto-rotate");
    if ((await autoRotateToggle.getAttribute("aria-pressed")) === "true") {
      await autoRotateToggle.click();
    }
    await page.evaluate(() => {
      const iframe = document.querySelector('iframe[title="sogs-migrated-viewer"]');
      iframe?.contentWindow?.postMessage({ type: "sogs:cameraMode", mode: "free" }, "*");
    });
    await page.waitForTimeout(500);
  }

  const canvas = page.frameLocator('iframe[title="sogs-migrated-viewer"]').locator("canvas");
  await canvas.waitFor({ state: "visible", timeout: LOAD_TIMEOUT_MS });
  const box = await canvas.boundingBox();
  assert(box, "viewer canvas should have a bounding box");

  const centerX = box.x + box.width / 2;
  const centerY = box.y + box.height / 2;

  const before = await readCamera(frame);
  assert(before, `${testCase.name} camera should exist before navigation`);

  await page.mouse.move(centerX, centerY);
  await page.mouse.down();
  await page.mouse.move(centerX + 140, centerY + 60, { steps: 12 });
  await page.mouse.up();
  await page.waitForTimeout(500);

  const afterOrbit = await readCamera(frame);
  const orbitChanged = cameraDelta(before, afterOrbit) > 0.001;

  await page.mouse.move(centerX, centerY);
  await page.mouse.wheel(0, 500);
  await page.waitForTimeout(500);

  const afterZoom = await readCamera(frame);
  assert(cameraDelta(afterOrbit, afterZoom) > 0.001, `${testCase.name} camera should change after zoom navigation`);

  return { before, afterOrbit, afterZoom, orbitChanged };
}

(async () => {
  await fs.mkdir(logsDir, { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const results = [];

  for (const testCase of CASES) {
    const { splatFrame, renderStats } = await loadCase(page, testCase);
    const cameraStates = testCase.verifyNavigation ? await verifyNavigation(page, splatFrame, testCase) : null;

    const screenshotPath = path.join(logsDir, `sogs-migrated-viewer-${testCase.name}.png`);
    await page.screenshot({ path: screenshotPath, fullPage: true });

    results.push({
      name: testCase.name,
      stage: testCase.expectedStage,
      renderStats,
      cameraStates,
      screenshotPath,
    });
  }

  const summaryPath = path.join(logsDir, "sogs-migrated-viewer-results.json");
  await fs.writeFile(summaryPath, JSON.stringify(results, null, 2));
  console.log(JSON.stringify({ ok: true, summaryPath, results }, null, 2));
  await browser.close();
})().catch((error) => {
  console.error("Unexpected failure while running SOGS migrated viewer tests", error);
  process.exit(1);
});
