/**
 * E2E checks for /sogs-viewer: auto-load, manual reload, ?url= override, site chrome elsewhere.
 *
 * Usage (from repo root or web/):
 *   cd web && SOGS_VIEWER_URL=http://127.0.0.1:3001 node scripts/test-sogs-viewer.mjs
 *
 * Env:
 *   SOGS_VIEWER_URL   — base URL (default: Cloudflare preview in repo)
 *   SOGS_BUNDLE_URL   — HTTPS lod-meta.json/meta.json or bundle folder URL
 *   SOGS_SCENARIOS    — comma list: chromium-desktop, webkit-mobile
 */

import { chromium, webkit } from "playwright";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, "..", "..");
const logsDir = path.join(repoRoot, "logs");

const DEFAULT_PREVIEW = "https://agent-48291037-sogs-viewer.v0-spaceport-website-preview2.pages.dev";
const DEFAULT_BUNDLE =
  "https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-r5-v18-splattransform-lod-nosingle-public-1777575472/supersplat_bundle/lod-meta.json";

const previewUrl = (process.env.SOGS_VIEWER_URL ?? DEFAULT_PREVIEW).replace(/\/$/, "");
const bundleUrl = process.env.SOGS_BUNDLE_URL ?? DEFAULT_BUNDLE;

const scenarios = [
  {
    name: "chromium-desktop",
    launcher: chromium,
    options: { viewport: { width: 1400, height: 900 } },
  },
  {
    name: "webkit-mobile",
    launcher: webkit,
    options: {
      viewport: { width: 414, height: 896 },
      userAgent:
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    },
  },
];
const requestedScenarios = process.env.SOGS_SCENARIOS
  ? process.env.SOGS_SCENARIOS.split(",")
      .map((s) => s.trim())
      .filter(Boolean)
  : null;
const activeScenarios = requestedScenarios?.length
  ? scenarios.filter((scenario) => requestedScenarios.includes(scenario.name))
  : scenarios;
if (!activeScenarios.length) {
  console.error("No matching scenarios to run.");
  process.exit(1);
}

const inputSelector = "#sogs-url-input";
const submitSelector = 'button[type="submit"]';
const iframeSelector = 'iframe[title="sogs-viewer"]';

async function ensureLogsDir() {
  await fs.mkdir(logsDir, { recursive: true });
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

async function runScenario({ launcher, name, options }) {
  const consoleBuffer = [];
  const browser = await launcher.launch();
  const context = await browser.newContext(options);
  const page = await context.newPage();

  page.on("console", (msg) => {
    consoleBuffer.push(`[${msg.type()}] ${msg.text()}`);
  });

  const screenshotPath = path.join(logsDir, `sogs-viewer-${name}.png`);
  const consolePath = path.join(logsDir, `sogs-viewer-${name}-console.log`);

  try {
    // --- Standalone page: no site header/footer ---
    await page.goto(`${previewUrl}/sogs-viewer`, { waitUntil: "domcontentloaded", timeout: 120000 });
    await page.waitForSelector(inputSelector, { timeout: 15000 });
    assert((await page.locator("header").count()) === 0, "sogs-viewer should not render main site <header>");
    assert((await page.getByRole("link", { name: "Spaceport Home" }).count()) === 0, "no Spaceport Home nav link on standalone viewer");

    // Prefilled default bundle + auto-load on mount
    await expectInputHasBundle(page);
    await page.waitForSelector(iframeSelector, { timeout: 60000 });
    await page.getByText(/Ready [-—]/).waitFor({ state: "visible", timeout: 360000 });

    const splatFrame = page.frames().find((f) => f.url().includes("supersplat-lod-viewer") || f.url().includes("supersplat-viewer"));
    assert(!!splatFrame, "supersplat iframe frame should exist");
    const xzReady = await splatFrame.evaluate(() => window.__sogsSplatXzDragReady === true);
    assert(xzReady, "sogs-bridge should set __sogsSplatXzDragReady on the viewer canvas");
    await expectLodMetricsWhenRequested(page);

    // Manual reload still works
    await page.click(submitSelector);
    await page.getByText(/Loading bundle/).waitFor({ state: "visible", timeout: 5000 }).catch(() => {});
    await page.getByText(/Ready [-—]/).waitFor({ state: "visible", timeout: 360000 });

    // ?url= override (encoded)
    const encoded = encodeURIComponent(bundleUrl);
    await page.goto(`${previewUrl}/sogs-viewer?url=${encoded}`, { waitUntil: "domcontentloaded", timeout: 60000 });
    await page.waitForSelector(iframeSelector, { timeout: 60000 });
    await expectInputHasBundle(page, new URL(bundleUrl).host);
    await page.getByText(/Ready [-—]/).waitFor({ state: "visible", timeout: 360000 });
    await expectLodMetricsWhenRequested(page);

    // Non-HTTP URL is rejected — wait for auto-load to finish first or the mount effect overwrites the field
    await page.goto(`${previewUrl}/sogs-viewer`, { waitUntil: "domcontentloaded", timeout: 60000 });
    await page.waitForSelector(iframeSelector, { timeout: 120000 });
    await page.getByText(/Ready [-—]/).waitFor({ state: "visible", timeout: 360000 });
    await page.fill(inputSelector, "ftp://example.com/bundle/");
    await page.click(submitSelector);
    await page.getByText(/Enter a valid HTTPS URL/).waitFor({ state: "visible", timeout: 30000 });

    // Main site still has chrome when leaving viewer
    await page.goto(`${previewUrl}/landing`, { waitUntil: "domcontentloaded", timeout: 60000 });
    await page.getByRole("link", { name: "Spaceport Home" }).waitFor({ state: "visible", timeout: 15000 });

    await page.screenshot({ path: screenshotPath, fullPage: true });
    await fs.writeFile(consolePath, consoleBuffer.join("\n"), "utf8");
    return { name, screenshotPath, consolePath };
  } catch (error) {
    await page.screenshot({ path: screenshotPath, fullPage: true }).catch(() => {});
    await fs.writeFile(consolePath, consoleBuffer.join("\n"), "utf8").catch(() => {});
    throw error;
  } finally {
    await browser.close();
  }
}

async function expectInputHasBundle(page, expectedHost = "spaceport-ml-processing.s3.amazonaws.com") {
  const val = await page.inputValue(inputSelector);
  assert(val.includes(expectedHost), `expected prefilled S3 bundle URL from ${expectedHost}`);
}

async function expectLodMetricsWhenRequested(page) {
  if (!bundleUrl.includes("lod-meta.json")) {
    return;
  }
  const metrics = page.getByTestId("sogs-bundle-metrics");
  await metrics.waitFor({ state: "attached", timeout: 30000 });
  const attrs = await metrics.evaluate((node) => ({
    kind: node.getAttribute("data-bundle-kind"),
    rootFile: node.getAttribute("data-root-file"),
    chunkFiles: Number(node.getAttribute("data-chunk-files") || "0"),
    loadedNodes: Number(node.getAttribute("data-loaded-nodes") || "0"),
    firstFrameMs: node.getAttribute("data-first-frame-ms"),
  }));
  assert(attrs.kind === "lod-streaming", `expected lod-streaming bundle, got ${attrs.kind}`);
  assert(attrs.rootFile === "lod-meta.json", `expected lod-meta.json root, got ${attrs.rootFile}`);
  assert(attrs.chunkFiles > 0, "expected LOD chunk files");
  assert(attrs.loadedNodes > 0, "expected loaded LOD nodes");
  assert(Boolean(attrs.firstFrameMs), "expected first frame telemetry");
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
    await fs.writeFile(summaryPath, JSON.stringify({ previewUrl, bundleUrl, results }, null, 2));
    console.log(`Results saved to ${summaryPath}`);
  }
})().catch((error) => {
  console.error("Unexpected failure while running SOGS viewer tests", error);
  process.exitCode = 1;
});
