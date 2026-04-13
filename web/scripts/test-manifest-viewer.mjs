/**
 * Smoke test for manifest viewers, defaulting to /viewer/meadow-ln.
 *
 * Usage (from web/):
 *   VIEWER_BASE_URL=http://127.0.0.1:3000 node scripts/test-manifest-viewer.mjs
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

const baseUrl = (process.env.VIEWER_BASE_URL ?? "http://127.0.0.1:3000").replace(/\/$/, "");
const slug = process.env.VIEWER_SLUG ?? "meadow-ln";
const route = `/viewer/${slug}`;
const iframeTitle = process.env.VIEWER_IFRAME_TITLE ?? "meadow-ln-viewer";
const expectedSkyboxSubstring =
  process.env.VIEWER_EXPECT_SKYBOX_SUBSTRING?.trim() || "background_skybox.webp";
const expectedDetailsHeading = process.env.VIEWER_EXPECT_DETAILS_HEADING ?? "Incognito";
const expectedDetailsLead =
  process.env.VIEWER_EXPECT_DETAILS_LEAD?.trim() || "Tucked into nearly 30 acres beneath the Bridger Mountains";

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
  let alpha = 0;
  for (let index = 0; index < pixels.length; index += 4) {
    if (pixels[index + 3] > 0) alpha += 1;
    if (pixels[index] + pixels[index + 1] + pixels[index + 2] > 36) bright += 1;
  }
  return { width, height, bright, alpha };
}

function cameraDelta(a, b) {
  return Math.hypot(
    (a?.x ?? 0) - (b?.x ?? 0),
    (a?.y ?? 0) - (b?.y ?? 0),
    (a?.z ?? 0) - (b?.z ?? 0),
  );
}

async function clickUntilTapRing(page, frameLocator) {
  const positions = [
    { x: 720, y: 450 },
    { x: 600, y: 450 },
    { x: 840, y: 450 },
    { x: 720, y: 330 },
    { x: 720, y: 570 },
  ];

  for (const position of positions) {
    await frameLocator.click({ position });
    try {
      await page.waitForSelector(".sogs-tap-pick-feedback", { timeout: 1500 });
      return position;
    } catch {
      /* try the next likely hit point */
    }
  }

  throw new Error("expected tap ring feedback after clicking a focusable point in the viewer");
}

async function assertTapRingVisible(page) {
  await page.waitForSelector(".sogs-tap-pick-feedback", { timeout: 1500 });
  const ring = page.locator(".sogs-tap-pick-feedback").first();
  const state = await ring.evaluate((element) => ({
    text: (element.textContent ?? "").trim(),
    opacity: Number.parseFloat(getComputedStyle(element).opacity || "0"),
  }));
  assert(state.text === "", `tap ring should not render text content, got ${JSON.stringify(state.text)}`);
  assert(state.opacity > 0.05, `tap ring should be visibly animating, got opacity ${state.opacity}`);
}

(async () => {
  await fs.mkdir(logsDir, { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const skyboxResponses = [];

  page.on("response", (response) => {
    if (response.url().includes(expectedSkyboxSubstring)) {
      skyboxResponses.push({ url: response.url(), status: response.status() });
    }
  });

  await page.goto(`${baseUrl}${route}?dev=1`, {
    waitUntil: "domcontentloaded",
    timeout: 120000,
  });

  assert((await page.locator("header").count()) === 0, "standalone manifest viewer should not render site header");
  await page.waitForSelector(`iframe[title="${iframeTitle}"]`, { timeout: 60000 });

  const iframeHandle = await page.locator(`iframe[title="${iframeTitle}"]`).elementHandle();
  const viewerFrame = await iframeHandle?.contentFrame();
  assert(!!viewerFrame, "viewer iframe frame exists");

  await viewerFrame.waitForFunction(() => window.__sogsSplatXzDragReady === true, null, {
    timeout: 120000,
  });
  await viewerFrame.waitForFunction(() => {
    const cam = window.__sogsCtx?.viewer?.cameraManager?.camera;
    return !!cam && [cam.position.x, cam.position.y, cam.position.z, cam.distance].every(Number.isFinite);
  }, null, { timeout: 120000 });
  await page.waitForFunction(() => {
    const button = document.querySelector("#detailsButton");
    return button instanceof HTMLButtonElement && !button.disabled;
  }, null, { timeout: 120000 });
  assert((await page.locator('[data-testid="focus-scene-center"]').count()) === 0, "reference viewer should not render focus-scene-center button");
  await page.waitForSelector("#compassButton", { timeout: 10000 });

  const detailsIconSrc = await page.locator("#detailsButton img").getAttribute("src");
  assert(
    detailsIconSrc?.includes("DetailsIconDefault.svg"),
    `expected reference details icon, got ${detailsIconSrc ?? "missing"}`,
  );
  const compassAriaLabel = await page.locator("#compassButton").getAttribute("aria-label");
  assert(
    compassAriaLabel === "Go to animation start",
    `expected reference compass aria label, got ${compassAriaLabel ?? "missing"}`,
  );

  await page.locator("#detailsButton").evaluate((button) => button.click());
  await page.waitForSelector("#detailsBox.show", { timeout: 10000 });
  await page.waitForSelector("#overlay-ui.active", { timeout: 10000 });
  const detailsHeading = (await page.locator("#canyon-details-heading").textContent())?.trim();
  assert(detailsHeading === expectedDetailsHeading, `expected details heading ${expectedDetailsHeading}, got ${detailsHeading ?? "missing"}`);
  const detailsText = (await page.locator("#detailsContent").textContent())?.trim() ?? "";
  assert(
    detailsText.includes(expectedDetailsLead),
    `expected details body to include reference copy substring "${expectedDetailsLead}"`,
  );
  await page.keyboard.press("Escape");
  await page.waitForFunction(() => !document.querySelector("#detailsBox")?.classList.contains("show"), null, { timeout: 10000 });

  const readCameraPosition = async () =>
    viewerFrame.evaluate(() => {
      const camera = window.__sogsCtx?.viewer?.cameraManager?.camera;
      return camera
        ? { x: camera.position.x, y: camera.position.y, z: camera.position.z }
        : null;
    });

  const motionStart = await readCameraPosition();
  await page.waitForTimeout(700);
  const motionMid = await readCameraPosition();
  assert(
    cameraDelta(motionStart, motionMid) > 0.01,
    `expected intro animation to move camera before interaction, got delta ${cameraDelta(motionStart, motionMid)}`,
  );

  await clickUntilTapRing(page, viewerFrame.locator("canvas"));
  await page.waitForTimeout(300);
  await assertTapRingVisible(page);

  await page.waitForTimeout(900);
  await clickUntilTapRing(page, viewerFrame.locator("canvas"));
  await page.waitForTimeout(300);
  await assertTapRingVisible(page);

  const stopStart = await readCameraPosition();
  await page.waitForTimeout(900);
  const stopEnd = await readCameraPosition();
  assert(
    cameraDelta(stopStart, stopEnd) < 0.01,
    `expected user interaction to stop scripted movement, got delta ${cameraDelta(stopStart, stopEnd)}`,
  );

  const renderBuffer = await page.locator(`iframe[title="${iframeTitle}"]`).screenshot();
  const renderStats = summarizeRenderedPixels(renderBuffer);
  assert(
    renderStats.alpha > 0 && renderStats.bright > 5000,
    `viewer iframe should render visible content, got stats ${JSON.stringify(renderStats)}`,
  );
  assert(
    skyboxResponses.some((response) => response.status === 200),
    `expected skybox request containing "${expectedSkyboxSubstring}", got ${JSON.stringify(skyboxResponses)}`,
  );

  await page.getByTestId("path-editor-toggle").click();
  await page.waitForSelector('[data-testid="animation-path-panel"].active', { timeout: 10000 });
  await page.waitForSelector('[data-testid="animation-path-checkpoints"] .animation-checkpoint-item', {
    timeout: 10000,
  });

  const shot = path.join(logsDir, `manifest-viewer-${slug}-smoke.png`);
  await page.screenshot({ path: shot, fullPage: true });
  console.log(`Render stats: ${JSON.stringify(renderStats)}`);
  console.log(`Skybox responses: ${JSON.stringify(skyboxResponses)}`);
  console.log(`OK — screenshot ${shot}`);
  await browser.close();
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
