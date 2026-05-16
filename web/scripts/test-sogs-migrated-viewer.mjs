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
import zlib from "node:zlib";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, "..", "..");
const logsDir = path.join(repoRoot, "logs");

const baseUrl = (process.env.SOGS_MIGRATED_URL ?? "http://127.0.0.1:3000").replace(/\/$/, "");
const bundleUrl =
  process.env.SOGS_BUNDLE_URL ??
  "https://spaceport-ml-processing.s3.amazonaws.com/compressed/sogs-test-1763664401/supersplat_bundle/meta.json";
const disableSkybox =
  process.env.SOGS_DISABLE_SKYBOX === "1" ||
  process.env.SOGS_DISABLE_SKYBOX === "true" ||
  process.env.SOGS_DISABLE_SKYBOX === "yes";
const skyboxOverride = process.env.SOGS_SKYBOX_OVERRIDE?.trim() || "";
const expectedSkyboxSubstring =
  process.env.SOGS_EXPECT_SKYBOX_SUBSTRING?.trim() || "/supersplat-viewer/skybox/kloppenheim_06_puresky_equirect.png";
const expectBundledSkybox =
  process.env.SOGS_EXPECT_BUNDLED_SKYBOX === "1" || process.env.SOGS_EXPECT_BUNDLED_SKYBOX === "true";

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

async function readCanvasStats(frame) {
  return frame.evaluate(async () => {
    const cam = window.__sogsCtx?.viewer?.cameraManager?.camera;
    return {
      camera: cam
        ? {
            position: { x: cam.position.x, y: cam.position.y, z: cam.position.z },
            angles: { x: cam.angles.x, y: cam.angles.y, z: cam.angles.z },
            distance: cam.distance,
          }
        : null,
    };
  });
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
  let alpha = 0;
  for (let i = 0; i < pixels.length; i += 4) {
    if (pixels[i + 3] > 0) alpha += 1;
    if (pixels[i] + pixels[i + 1] + pixels[i + 2] > 36) bright += 1;
  }
  return { width, height, bright, alpha };
}

(async () => {
  await fs.mkdir(logsDir, { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  const skyboxResponses = [];

  page.on("response", (response) => {
    if (response.url().includes(expectedSkyboxSubstring)) {
      skyboxResponses.push({ url: response.url(), status: response.status() });
    }
  });

  const encoded = encodeURIComponent(bundleUrl);
  let skyboxQuery = "";
  if (disableSkybox) {
    skyboxQuery = "&skybox=off";
  } else if (skyboxOverride) {
    skyboxQuery = `&skybox=${encodeURIComponent(skyboxOverride)}`;
  }
  await page.goto(`${baseUrl}/sogs-migrated-viewer?url=${encoded}${skyboxQuery}`, {
    waitUntil: "domcontentloaded",
    timeout: 120000,
  });

  assert((await page.locator("header").count()) === 0, "no site header on standalone migrated viewer");
  await page.waitForSelector('iframe[title="sogs-migrated-viewer"]', { timeout: 60000 });

  const iframeHandle = await page.locator('iframe[title="sogs-migrated-viewer"]').elementHandle();
  const splatFrame = await iframeHandle?.contentFrame();
  assert(!!splatFrame, "supersplat iframe frame exists");
  await splatFrame.waitForFunction(() => window.__sogsSplatXzDragReady === true, null, {
    timeout: 120000,
  });
  await page.waitForFunction(() => {
    const button = document.querySelector('[data-testid="focus-scene-center"]');
    return button instanceof HTMLButtonElement && !button.disabled;
  }, null, { timeout: 120000 });
  await splatFrame.waitForFunction(() => {
    const cam = window.__sogsCtx?.viewer?.cameraManager?.camera;
    return !!cam && [cam.position.x, cam.position.y, cam.position.z, cam.distance].every(Number.isFinite);
  }, null, { timeout: 120000 });

  const stats = await readCanvasStats(splatFrame);
  const renderBuffer = await page.locator('iframe[title="sogs-migrated-viewer"]').screenshot();
  const renderStats = summarizeRenderedPixels(renderBuffer);
  assert(!!stats.camera, "camera should be available inside the migrated viewer iframe");
  assert(
    [stats.camera.position.x, stats.camera.position.y, stats.camera.position.z, stats.camera.distance].every(
      Number.isFinite,
    ),
    `camera pose should stay finite: ${JSON.stringify(stats.camera)}`,
  );
  assert(
    renderStats.alpha > 0 && renderStats.bright > 5000,
    `viewer iframe should render visible content, got stats ${JSON.stringify(renderStats)}`,
  );
  if (expectBundledSkybox) {
    assert(
      skyboxResponses.some((response) => response.status === 200),
      `expected bundled skybox request containing "${expectedSkyboxSubstring}", got ${JSON.stringify(skyboxResponses)}`,
    );
  }
  if (disableSkybox) {
    assert(
      skyboxResponses.length === 0,
      `expected no skybox requests when disabled, got ${JSON.stringify(skyboxResponses)}`,
    );
  }

  await page.getByTestId("sogs-hole-picker").waitFor({ state: "visible", timeout: 10000 });
  await page.getByTestId("focus-scene-center").waitFor({ state: "visible", timeout: 10000 });
  await page.getByTestId("path-editor-toggle").click();
  await page.waitForSelector('[data-testid="animation-path-panel"].active', { timeout: 10000 });
  await page.waitForSelector('[data-testid="animation-path-checkpoints"] .animation-checkpoint-item', {
    timeout: 10000,
  });

  const shot = path.join(logsDir, disableSkybox ? "sogs-migrated-viewer-nosky.png" : "sogs-migrated-viewer-smoke.png");
  await page.screenshot({ path: shot, fullPage: true });
  console.log(`Canvas stats: ${JSON.stringify(stats)}`);
  console.log(`Render stats: ${JSON.stringify(renderStats)}`);
  if (expectBundledSkybox) {
    console.log(`Skybox responses: ${JSON.stringify(skyboxResponses)}`);
  }
  console.log(`OK — screenshot ${shot}`);
  await browser.close();
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
