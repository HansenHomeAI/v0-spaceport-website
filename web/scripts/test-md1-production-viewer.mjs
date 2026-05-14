/**
 * Smoke test for /md1-viewer production LOD loading.
 *
 * Usage:
 *   cd web
 *   MD1_VIEWER_URL=http://127.0.0.1:3031 \
 *   MD1_LOD_URL=https://.../lod-meta.json \
 *   node scripts/test-md1-production-viewer.mjs
 */

import { chromium } from "playwright";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, "..", "..");
const logsDir = path.join(repoRoot, "logs");

const baseUrl = (process.env.MD1_VIEWER_URL ?? "http://127.0.0.1:3031").replace(/\/$/, "");
const lodUrl =
  process.env.MD1_LOD_URL ??
  "https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-r5-v18-splattransform-lod-nosingle-public-1777575472/supersplat_bundle/lod-meta.json";
const expectedChunkSubstring = process.env.MD1_EXPECT_CHUNK_SUBSTRING?.trim() || "";
const playwrightChannel = process.env.PLAYWRIGHT_CHANNEL?.trim() || "";

const scenarios = [
  { name: "desktop", viewport: { width: 1440, height: 960 }, query: "" },
  { name: "mobile", viewport: { width: 414, height: 896 }, query: "" },
];

if (process.env.MD1_RUN_COARSE_LOD === "1") {
  scenarios.push({ name: "coarse-lod", viewport: { width: 1440, height: 960 }, query: "&lodMin=3&lodMax=3" });
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

function parseIntOrNull(value) {
  const parsed = Number.parseInt(value ?? "", 10);
  return Number.isFinite(parsed) ? parsed : null;
}

function parseFloatOrNull(value) {
  const parsed = Number.parseFloat(value ?? "");
  return Number.isFinite(parsed) ? parsed : null;
}

function unfilterPngScanline(filter, line, previous, bytesPerPixel) {
  const output = Buffer.allocUnsafe(line.length);
  for (let index = 0; index < line.length; index += 1) {
    const left = index >= bytesPerPixel ? output[index - bytesPerPixel] : 0;
    const up = previous ? previous[index] : 0;
    const upLeft = previous && index >= bytesPerPixel ? previous[index - bytesPerPixel] : 0;
    let predictor = 0;
    if (filter === 1) {
      predictor = left;
    } else if (filter === 2) {
      predictor = up;
    } else if (filter === 3) {
      predictor = Math.floor((left + up) / 2);
    } else if (filter === 4) {
      const p = left + up - upLeft;
      const pa = Math.abs(p - left);
      const pb = Math.abs(p - up);
      const pc = Math.abs(p - upLeft);
      predictor = pa <= pb && pa <= pc ? left : pb <= pc ? up : upLeft;
    }
    output[index] = (line[index] + predictor) & 0xff;
  }
  return output;
}

async function analyzePng(pathname) {
  const zlib = await import("node:zlib");
  const file = await fs.readFile(pathname);
  assert(file.subarray(0, 8).equals(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10])), "screenshot is not PNG");
  let offset = 8;
  let width = 0;
  let height = 0;
  let colorType = 0;
  const idat = [];
  while (offset < file.length) {
    const length = file.readUInt32BE(offset);
    const type = file.toString("ascii", offset + 4, offset + 8);
    const data = file.subarray(offset + 8, offset + 8 + length);
    if (type === "IHDR") {
      width = data.readUInt32BE(0);
      height = data.readUInt32BE(4);
      colorType = data[9];
      assert(data[8] === 8, "only 8-bit PNG screenshots are supported");
      assert(colorType === 2 || colorType === 6, "only RGB/RGBA PNG screenshots are supported");
    } else if (type === "IDAT") {
      idat.push(data);
    } else if (type === "IEND") {
      break;
    }
    offset += 12 + length;
  }
  const channels = colorType === 6 ? 4 : 3;
  const rowLength = width * channels;
  const inflated = zlib.inflateSync(Buffer.concat(idat));
  let rowOffset = 0;
  let previous = null;
  let sampled = 0;
  let visible = 0;
  let bright = 0;
  let dark = 0;
  let sum = 0;
  let sumSquared = 0;
  let colorSpread = 0;
  const step = Math.max(1, Math.floor(Math.min(width, height) / 160));

  for (let y = 0; y < height; y += 1) {
    const filter = inflated[rowOffset];
    const line = inflated.subarray(rowOffset + 1, rowOffset + 1 + rowLength);
    const row = unfilterPngScanline(filter, line, previous, channels);
    if (y % step === 0) {
      for (let x = 0; x < width; x += step) {
        const index = x * channels;
        const r = row[index];
        const g = row[index + 1];
        const b = row[index + 2];
        const luma = 0.2126 * r + 0.7152 * g + 0.0722 * b;
        sampled += 1;
        sum += luma;
        sumSquared += luma * luma;
        colorSpread += Math.max(r, g, b) - Math.min(r, g, b);
        if (luma > 8) {
          visible += 1;
        }
        if (luma > 96) {
          bright += 1;
        }
        if (luma < 5) {
          dark += 1;
        }
      }
    }
    previous = row;
    rowOffset += rowLength + 1;
  }

  const mean = sum / Math.max(sampled, 1);
  const variance = sumSquared / Math.max(sampled, 1) - mean * mean;
  return {
    width,
    height,
    sampled,
    visibleRatio: visible / Math.max(sampled, 1),
    brightRatio: bright / Math.max(sampled, 1),
    darkRatio: dark / Math.max(sampled, 1),
    meanLuma: mean,
    lumaStdDev: Math.sqrt(Math.max(variance, 0)),
    meanColorSpread: colorSpread / Math.max(sampled, 1),
  };
}

async function readMetrics(page) {
  const dataset = await page.locator('[data-testid="md1-bundle-metrics"]').evaluate((element) => ({
    ...element.dataset,
  }));
  return {
    bundleKind: dataset.bundleKind ?? "",
    rootFile: dataset.rootFile ?? "",
    sourceUrl: dataset.sourceUrl ?? "",
    viewerUrl: dataset.viewerUrl ?? "",
    lodLevels: parseIntOrNull(dataset.lodLevels),
    chunkFiles: parseIntOrNull(dataset.chunkFiles),
    chunkMetaRequests: parseIntOrNull(dataset.chunkMetaRequests) ?? 0,
    firstFrameMs: parseFloatOrNull(dataset.firstFrameMs),
    lodMin: parseIntOrNull(dataset.lodMin),
    lodMax: parseIntOrNull(dataset.lodMax),
  };
}

async function readFrameMetrics(page) {
  const frame = page.frames().find((candidate) => candidate.url().includes("/supersplat-lod-viewer/index.html"));
  if (!frame) {
    return null;
  }
  return frame
    .evaluate(() => ({
      readyState: document.readyState,
      rootManifestType: window.__sogsNetworkMetrics?.rootManifestType ?? null,
      chunkMetaRequests: window.__sogsNetworkMetrics?.uniqueChunkMetaUrls?.length ?? 0,
      firstFrameMs:
        window.__sogsNetworkMetrics?.firstFrame &&
        Number.isFinite(window.__sogsNetworkMetrics.firstFrame.at) &&
        Number.isFinite(window.__sogsNetworkMetrics.loadStartedAt)
          ? window.__sogsNetworkMetrics.firstFrame.at - window.__sogsNetworkMetrics.loadStartedAt
          : null,
      hasContext: !!window.__sogsCtx?.app,
      hasGsplat: !!window.__sogsCtx?.app?.root?.findByName?.("gsplat"),
    }))
    .catch(() => null);
}

async function waitForReady(page, scenarioName) {
  await page.locator('[data-testid="md1-bundle-metrics"]').waitFor({ state: "attached", timeout: 120000 });
  const start = Date.now();
  let latest = null;
  let lastLog = 0;
  while (Date.now() - start < 180000) {
    latest = await readMetrics(page);
    if (latest.bundleKind === "lod-streaming" && latest.firstFrameMs && latest.firstFrameMs > 0) {
      console.log(
        `MD1 production viewer smoke: ${scenarioName} ready firstFrame=${latest.firstFrameMs.toFixed(1)}ms chunks=${latest.chunkMetaRequests}`,
      );
      return latest;
    }
    const elapsed = Date.now() - start;
    if (elapsed - lastLog >= 5000) {
      lastLog = elapsed;
      const frameMetrics = await readFrameMetrics(page);
      console.log(
        `MD1 production viewer smoke: ${scenarioName} waiting ${Math.round(elapsed / 1000)}s metrics=${JSON.stringify(latest)} frame=${JSON.stringify(frameMetrics)}`,
      );
    }
    await page.waitForTimeout(1000);
  }
  throw new Error(`timed out waiting for lod-streaming first frame; latest=${JSON.stringify(latest)}`);
}

async function waitForChunkTelemetry(page) {
  const start = Date.now();
  let latest = null;
  while (Date.now() - start < 30000) {
    latest = await readMetrics(page);
    if (latest.chunkMetaRequests > 0) {
      return latest;
    }
    await page.waitForTimeout(1000);
  }
  throw new Error(`timed out waiting for chunk telemetry; latest=${JSON.stringify(latest)}`);
}

async function closeScenarioContext(context, page) {
  await page.goto("about:blank", { waitUntil: "domcontentloaded", timeout: 5000 }).catch(() => {});
  await context.close().catch(() => {});
}

async function closeBrowser(browser) {
  let closed = false;
  await Promise.race([
    browser.close().then(() => {
      closed = true;
    }),
    new Promise((resolve) => setTimeout(resolve, 5000)),
  ]);
  if (!closed) {
    browser.process()?.kill("SIGKILL");
  }
}

async function runScenario(scenario) {
  console.log(`MD1 production viewer smoke: ${scenario.name}`);
  const browser = await chromium.launch({
    headless: true,
    ...(playwrightChannel ? { channel: playwrightChannel } : {}),
  });
  try {
    const context = await browser.newContext({ viewport: scenario.viewport });
    const page = await context.newPage();
    const responses = [];
    page.on("response", (response) => {
      responses.push({ url: response.url(), status: response.status() });
    });

    const encoded = encodeURIComponent(lodUrl);
    const url = `${baseUrl}/md1-viewer?url=${encoded}${scenario.query}`;
    await page.goto(url, { waitUntil: "domcontentloaded", timeout: 120000 });
    assert((await page.locator("header").count()) === 0, `${scenario.name}: md1-viewer should not render site header`);
    assert((await page.locator("footer").count()) === 0, `${scenario.name}: md1-viewer should not render site footer`);
    assert(
      (await page.locator("#footer-stats").count()) === 0,
      `${scenario.name}: md1-viewer should not render feedback footer panel`,
    );
    try {
      await waitForReady(page, scenario.name);
    } catch (error) {
      const metrics = await readMetrics(page).catch(() => null);
      await closeScenarioContext(context, page);
      throw new Error(
        `${scenario.name}: timed out waiting for production LOD readiness; metrics=${JSON.stringify(metrics)}`,
        {
          cause: error,
        },
      );
    }
    await waitForChunkTelemetry(page);
    await page.waitForTimeout(scenario.name === "mobile" ? 5000 : 1000);
    const metrics = await readMetrics(page);
    const screenshotPath = path.join(logsDir, `md1-production-viewer-${scenario.name}.png`);
    await page.screenshot({ path: screenshotPath, fullPage: false });
    const visualStats = await analyzePng(screenshotPath);
    await closeScenarioContext(context, page);

    const chunkMetaResponses = responses.filter((event) => event.url.endsWith("/meta.json"));
    assert(metrics.bundleKind === "lod-streaming", `${scenario.name}: expected lod-streaming, got ${metrics.bundleKind}`);
    assert(metrics.rootFile === "lod-meta.json", `${scenario.name}: expected lod-meta.json, got ${metrics.rootFile}`);
    assert(metrics.sourceUrl.includes("lod-meta.json"), `${scenario.name}: source URL should be lod-meta.json`);
    assert(metrics.chunkFiles && metrics.chunkFiles > 0, `${scenario.name}: manifest should advertise chunk files`);
    assert(metrics.chunkMetaRequests > 0, `${scenario.name}: viewer should request chunk meta files`);
    assert(metrics.firstFrameMs && metrics.firstFrameMs < 10000, `${scenario.name}: first frame exceeded 10s`);
    if (expectedChunkSubstring) {
      assert(
        chunkMetaResponses.some((event) => event.url.includes(expectedChunkSubstring)),
        `${scenario.name}: expected chunk URL containing ${expectedChunkSubstring}`,
      );
    } else {
      assert(chunkMetaResponses.length > 0, `${scenario.name}: expected at least one chunk meta response`);
    }
    assert(visualStats.visibleRatio > 0.03, `${scenario.name}: screenshot is visually empty`);
    assert(visualStats.lumaStdDev > 6, `${scenario.name}: screenshot has too little visual variation`);

    if (scenario.name === "coarse-lod") {
      assert(metrics.lodMin === 3 && metrics.lodMax === 3, "coarse-lod: URL LOD override was not applied");
    }

    return {
      scenario: scenario.name,
      metrics,
      visualStats,
      chunkMetaResponses: chunkMetaResponses.length,
      screenshotPath,
    };
  } finally {
    await closeBrowser(browser);
  }
}

await fs.mkdir(logsDir, { recursive: true });
const results = [];
for (const scenario of scenarios) {
  results.push(await runScenario(scenario));
}
const summaryPath = path.join(logsDir, "md1-production-viewer-results.json");
await fs.writeFile(summaryPath, JSON.stringify({ lodUrl, results }, null, 2));
console.log(`MD1 production viewer smoke passed: ${summaryPath}`);
