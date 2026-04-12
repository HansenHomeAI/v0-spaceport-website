/**
 * Deep validation for /sogs-viewer streamed LOD loading.
 *
 * Usage:
 *   cd web
 *   SOGS_VIEWER_URL=https://<preview> \
 *   SOGS_BUNDLE_URL=https://.../supersplat_bundle/lod-meta.json \
 *   node scripts/test-sogs-viewer.mjs
 */

import { chromium, webkit } from "playwright";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, "..", "..");
const logsDir = path.join(repoRoot, "logs");

const previewUrl = (process.env.SOGS_VIEWER_URL ?? "").replace(/\/$/, "");
const bundleUrl = (process.env.SOGS_BUNDLE_URL ?? "").trim();
if (!previewUrl || !bundleUrl) {
  console.error("Set SOGS_VIEWER_URL and SOGS_BUNDLE_URL before running this script.");
  process.exit(1);
}

const scenarios = [
  {
    name: "chromium-desktop",
    launcher: chromium,
    options: { viewport: { width: 1440, height: 960 } },
    expectedBudget: 3_000_000,
  },
  {
    name: "webkit-mobile",
    launcher: webkit,
    options: {
      viewport: { width: 414, height: 896 },
      userAgent:
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    },
    expectedBudget: 1_000_000,
  },
];

const requestedScenarios = process.env.SOGS_SCENARIOS
  ? process.env.SOGS_SCENARIOS.split(",")
      .map((value) => value.trim())
      .filter(Boolean)
  : null;

const activeScenarios = requestedScenarios?.length
  ? scenarios.filter((scenario) => requestedScenarios.includes(scenario.name))
  : scenarios;

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

function parseVector(value) {
  return (value ?? "")
    .split(",")
    .map((entry) => Number.parseFloat(entry))
    .filter((entry) => Number.isFinite(entry));
}

function midpoint(min, max) {
  return min.map((value, index) => (value + max[index]) / 2);
}

async function ensureLogsDir() {
  await fs.mkdir(logsDir, { recursive: true });
}

async function readMetrics(page) {
  const dataset = await page.locator('[data-testid="sogs-bundle-metrics"]').evaluate((element) => ({
    ...element.dataset,
  }));
  return {
    bundleKind: dataset.bundleKind ?? "",
    transport: dataset.transport ?? "",
    rootFile: dataset.rootFile ?? "",
    sourceUrl: dataset.sourceUrl ?? "",
    lodLevels: parseIntOrNull(dataset.lodLevels),
    chunkFiles: parseIntOrNull(dataset.chunkFiles),
    loadedNodes: parseIntOrNull(dataset.loadedNodes) ?? 0,
    chunkMetaRequests: parseIntOrNull(dataset.chunkMetaRequests) ?? 0,
    chunkMetaAtFirstFrame: parseIntOrNull(dataset.chunkMetaAtFirstFrame),
    firstFrameMs: parseFloatOrNull(dataset.firstFrameMs),
    splatBudget: parseIntOrNull(dataset.splatBudget),
    lodMin: parseIntOrNull(dataset.lodMin),
    lodMax: parseIntOrNull(dataset.lodMax),
    boundsMin: parseVector(dataset.boundsMin),
    boundsMax: parseVector(dataset.boundsMax),
  };
}

async function waitForStreamingReady(page) {
  await page.locator('[data-testid="sogs-bundle-metrics"]').waitFor({ state: "attached", timeout: 120000 });
  await page.waitForFunction(() => {
    const element = document.querySelector('[data-testid="sogs-bundle-metrics"]');
    if (!(element instanceof HTMLElement)) {
      return false;
    }
    return element.dataset.bundleKind === "lod-streaming" && element.dataset.chunkMetaRequests !== undefined;
  }, null, { timeout: 120000 });
}

async function requestViewerState(page) {
  await page.evaluate(() => {
    const iframe = document.querySelector('iframe[title="sogs-viewer"]');
    if (!(iframe instanceof HTMLIFrameElement) || !iframe.contentWindow) {
      throw new Error("viewer iframe missing");
    }
    iframe.contentWindow.postMessage({ type: "sogs:requestState" }, "*");
  });
}

async function postCameraPose(page, position, target) {
  await page.evaluate(
    ({ position: nextPosition, target: nextTarget }) => {
      const iframe = document.querySelector('iframe[title="sogs-viewer"]');
      if (!(iframe instanceof HTMLIFrameElement) || !iframe.contentWindow) {
        throw new Error("viewer iframe missing");
      }
      iframe.contentWindow.postMessage({ type: "sogs:cameraMode", mode: "scripted" }, "*");
      iframe.contentWindow.postMessage(
        {
          type: "sogs:cameraLookAt",
          position: nextPosition,
          target: nextTarget,
          fov: 60,
        },
        "*",
      );
      iframe.contentWindow.postMessage({ type: "sogs:requestState" }, "*");
    },
    { position, target },
  );
}

function buildSweepPoses(boundsMin, boundsMax) {
  const center = midpoint(boundsMin, boundsMax);
  const span = boundsMax.map((value, index) => Math.max(1, value - boundsMin[index]));
  return [
    {
      position: [boundsMin[0] - span[0] * 0.8, center[1] + span[1] * 0.35 + 1.5, center[2] + span[2] * 0.35 + 5],
      target: [boundsMin[0], center[1], center[2]],
    },
    {
      position: [boundsMax[0] + span[0] * 0.8, center[1] + span[1] * 0.35 + 1.5, center[2] + span[2] * 0.35 + 5],
      target: [boundsMax[0], center[1], center[2]],
    },
  ];
}

async function runInvalidUrlCheck(page) {
  await page.goto(`${previewUrl}/sogs-viewer`, { waitUntil: "domcontentloaded", timeout: 120000 });
  await page.locator("#sogs-url-input").waitFor({ timeout: 30000 });
  await page.fill("#sogs-url-input", "ftp://example.com/bundle/");
  await page.click('button[type="submit"]');
  await page.getByText(/Enter a valid HTTPS URL/i).waitFor({ state: "visible", timeout: 30000 });
}

async function runFolderProbeCheck(page) {
  if (!bundleUrl.includes("lod-meta.json")) {
    return null;
  }
  const folderUrl = bundleUrl.replace(/lod-meta\.json(?:\?.*)?$/, "");
  await page.goto(`${previewUrl}/sogs-viewer?url=${encodeURIComponent(folderUrl)}`, {
    waitUntil: "domcontentloaded",
    timeout: 120000,
  });
  await waitForStreamingReady(page);
  const metrics = await readMetrics(page);
  assert(metrics.rootFile === "lod-meta.json", `folder probe should resolve lod-meta.json, got ${metrics.rootFile}`);
  return metrics;
}

async function runScenario({ launcher, name, options, expectedBudget }) {
  const browser = await launcher.launch();
  const context = await browser.newContext(options);
  const page = await context.newPage();

  const consoleBuffer = [];
  const networkEvents = [];

  page.on("console", (message) => {
    consoleBuffer.push(`[${message.type()}] ${message.text()}`);
  });

  page.on("response", async (response) => {
    const url = response.url();
    if (url.includes("lod-meta.json") || /\/\d+_\d+\//.test(url) || url.endsWith("/meta.json")) {
      networkEvents.push({
        url,
        status: response.status(),
        frame: response.frame()?.url() ?? "",
      });
    }
  });

  const screenshotPath = path.join(logsDir, `sogs-viewer-${name}.png`);
  const consolePath = path.join(logsDir, `sogs-viewer-${name}-console.log`);
  const networkPath = path.join(logsDir, `sogs-viewer-${name}-network.json`);

  try {
    await page.goto(`${previewUrl}/sogs-viewer?url=${encodeURIComponent(bundleUrl)}`, {
      waitUntil: "domcontentloaded",
      timeout: 120000,
    });
    await page.locator("#sogs-url-input").waitFor({ timeout: 30000 });
    assert((await page.locator("header").count()) === 0, "sogs-viewer should not render the main site header");
    await waitForStreamingReady(page);
    await requestViewerState(page);

    const initialMetrics = await readMetrics(page);
    assert(initialMetrics.bundleKind === "lod-streaming", `expected lod-streaming bundle, got ${initialMetrics.bundleKind}`);
    assert(initialMetrics.transport === "direct", `expected direct transport for public S3 bundle, got ${initialMetrics.transport}`);
    assert(initialMetrics.rootFile === "lod-meta.json", `expected lod-meta.json root file, got ${initialMetrics.rootFile}`);
    assert(initialMetrics.splatBudget === expectedBudget, `expected budget ${expectedBudget}, got ${initialMetrics.splatBudget}`);
    assert(
      (initialMetrics.chunkFiles ?? 0) > 0,
      `expected chunk files for streamed bundle, got ${JSON.stringify(initialMetrics)}`,
    );
    assert(
      initialMetrics.firstFrameMs != null && initialMetrics.firstFrameMs > 0,
      `expected first frame timing, got ${JSON.stringify(initialMetrics)}`,
    );

    const poses = buildSweepPoses(initialMetrics.boundsMin, initialMetrics.boundsMax);
    for (const pose of poses) {
      await postCameraPose(page, pose.position, pose.target);
      await page.waitForTimeout(3500);
      await requestViewerState(page);
    }

    await page.waitForFunction(() => {
      const element = document.querySelector('[data-testid="sogs-bundle-metrics"]');
      if (!(element instanceof HTMLElement)) {
        return false;
      }
      const current = Number.parseInt(element.dataset.chunkMetaRequests ?? "", 10);
      const atFirstFrame = Number.parseInt(element.dataset.chunkMetaAtFirstFrame ?? "", 10);
      return Number.isFinite(current) && Number.isFinite(atFirstFrame) && current > atFirstFrame;
    }, null, { timeout: 120000 });

    const finalMetrics = await readMetrics(page);
    assert(
      finalMetrics.chunkMetaRequests > (initialMetrics.chunkMetaAtFirstFrame ?? 0),
      `camera sweeps should trigger more chunk requests: initial=${JSON.stringify(initialMetrics)} final=${JSON.stringify(finalMetrics)}`,
    );
    assert(
      finalMetrics.loadedNodes >= finalMetrics.chunkMetaRequests,
      `loaded nodes should track chunk requests: ${JSON.stringify(finalMetrics)}`,
    );

    const folderProbeMetrics = await runFolderProbeCheck(page);
    await runInvalidUrlCheck(page);

    await page.goto(`${previewUrl}/sogs-viewer?url=${encodeURIComponent(bundleUrl)}`, {
      waitUntil: "domcontentloaded",
      timeout: 120000,
    });
    await waitForStreamingReady(page);
    await page.screenshot({ path: screenshotPath, fullPage: true });
    await fs.writeFile(consolePath, consoleBuffer.join("\n"), "utf8");
    await fs.writeFile(
      networkPath,
      JSON.stringify(
        {
          previewUrl,
          bundleUrl,
          initialMetrics,
          finalMetrics,
          folderProbeMetrics,
          networkEvents,
        },
        null,
        2,
      ),
      "utf8",
    );

    return {
      name,
      initialMetrics,
      finalMetrics,
      folderProbeMetrics,
      screenshotPath,
      consolePath,
      networkPath,
    };
  } finally {
    await browser.close();
  }
}

(async () => {
  await ensureLogsDir();
  const results = [];

  for (const scenario of activeScenarios) {
    try {
      const result = await runScenario(scenario);
      results.push(result);
      console.log(`✓ ${scenario.name} completed`);
    } catch (error) {
      console.error(`✗ ${scenario.name} failed`, error);
      process.exitCode = 1;
    }
  }

  if (results.length) {
    const summaryPath = path.join(logsDir, "sogs-viewer-playwright-results.json");
    await fs.writeFile(summaryPath, JSON.stringify({ previewUrl, bundleUrl, results }, null, 2), "utf8");
    console.log(`Results saved to ${summaryPath}`);
  }
})().catch((error) => {
  console.error("Unexpected failure while running SOGS viewer tests", error);
  process.exitCode = 1;
});
