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
  "https://spaceport-ml-processing.s3.amazonaws.com/compressed/sogs-test-1763664401/supersplat_bundle/meta.json";

const previewUrl = process.env.SOGS_VIEWER_URL ?? DEFAULT_PREVIEW;
const bundleUrl = process.env.SOGS_BUNDLE_URL ?? DEFAULT_BUNDLE;
const expectSkybox = /^(1|true|yes)$/i.test(process.env.SOGS_EXPECT_SKYBOX ?? "");

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
  ? process.env.SOGS_SCENARIOS.split(",").map((s) => s.trim()).filter(Boolean)
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
const iframeSelector = 'iframe[title="SuperSplat Viewer"]';
const readyMessageSelector = expectSkybox
  ? 'text=SOGS bundle and baked skybox loaded.'
  : 'text=/SOGS bundle (and baked skybox )?loaded\\./';

async function sampleCanvasLuminance(frame) {
  return frame.evaluate(async () => {
    const sleep = (ms) => new Promise((resolve) => window.setTimeout(resolve, ms));
    const canvas = document.querySelector("canvas");
    if (!(canvas instanceof HTMLCanvasElement)) {
      return null;
    }

    await sleep(1500);

    const width = canvas.width || canvas.clientWidth;
    const height = canvas.height || canvas.clientHeight;
    if (!width || !height) {
      return null;
    }

    const sampleCanvas = document.createElement("canvas");
    sampleCanvas.width = width;
    sampleCanvas.height = height;

    const ctx = sampleCanvas.getContext("2d", { willReadFrequently: true });
    if (!ctx) {
      return null;
    }

    ctx.drawImage(canvas, 0, 0);

    const sampleWidth = Math.max(1, Math.floor(width * 0.25));
    const sampleHeight = Math.max(1, Math.floor(height * 0.2));
    const offsetX = Math.max(0, Math.floor((width - sampleWidth) / 2));
    const image = ctx.getImageData(offsetX, 0, sampleWidth, sampleHeight);

    let luminanceSum = 0;
    let nonBlackPixels = 0;
    const pixelCount = image.data.length / 4;

    for (let index = 0; index < image.data.length; index += 4) {
      const r = image.data[index];
      const g = image.data[index + 1];
      const b = image.data[index + 2];
      const luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b;
      luminanceSum += luminance;
      if (luminance > 8) {
        nonBlackPixels += 1;
      }
    }

    return {
      width,
      height,
      sampleWidth,
      sampleHeight,
      avgLuminance: pixelCount ? luminanceSum / pixelCount : 0,
      nonBlackRatio: pixelCount ? nonBlackPixels / pixelCount : 0,
    };
  });
}

async function ensureLogsDir() {
  await fs.mkdir(logsDir, { recursive: true });
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
    await page.goto(`${previewUrl}/sogs-viewer`, { waitUntil: "domcontentloaded", timeout: 120000 });
    await page.waitForSelector(inputSelector, { timeout: 15000 });
    await page.waitForFunction(
      () => {
        const input = document.querySelector("#sogs-url-input");
        return input && !input.hasAttribute("disabled");
      },
      null,
      { timeout: 180000 }
    );
    await page.fill(inputSelector, bundleUrl);
    await page.click(submitSelector);
    await page.waitForSelector(iframeSelector, { timeout: 15000 });
    await page.waitForSelector('text=Viewer ready', { timeout: 360000 });
    await page.waitForSelector(readyMessageSelector, { timeout: 360000 });

    const iframeSrc = await page.locator(iframeSelector).getAttribute("src");
    const viewerFrame = page.frames().find((frame) => frame.url().includes("/supersplat-viewer/index.html"));
    if (!viewerFrame) {
      throw new Error("Could not resolve the embedded SuperSplat iframe.");
    }

    const skyboxUrl = await viewerFrame.evaluate(() => window.sse?.config?.skyboxUrl ?? null);
    const luminanceSample = await sampleCanvasLuminance(viewerFrame);

    if (expectSkybox && !iframeSrc?.includes("skybox=")) {
      throw new Error(`Expected iframe src to include skybox query param, got: ${iframeSrc}`);
    }

    if (expectSkybox && !skyboxUrl) {
      throw new Error("Expected embedded viewer to receive a skyboxUrl, but none was present.");
    }

    if (expectSkybox) {
      if (!luminanceSample) {
        throw new Error("Could not sample viewer canvas luminance for skybox validation.");
      }
      if (luminanceSample.avgLuminance <= 8 || luminanceSample.nonBlackRatio <= 0.1) {
        throw new Error(
          `Skybox validation failed: avgLuminance=${luminanceSample.avgLuminance}, nonBlackRatio=${luminanceSample.nonBlackRatio}`,
        );
      }
    }

    await page.screenshot({ path: screenshotPath, fullPage: true });
    await fs.writeFile(consolePath, consoleBuffer.join("\n"), "utf8");
    return { name, screenshotPath, consolePath, iframeSrc, skyboxUrl, luminanceSample };
  } catch (error) {
    // capture failure state
    await page.screenshot({ path: screenshotPath, fullPage: true }).catch(() => {});
    await fs.writeFile(consolePath, consoleBuffer.join("\n"), "utf8").catch(() => {});
    throw error;
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
    await fs.writeFile(summaryPath, JSON.stringify({ previewUrl, bundleUrl, results }, null, 2));
    console.log(`Results saved to ${summaryPath}`);
  }
})().catch((error) => {
  console.error("Unexpected failure while running SOGS viewer tests", error);
  process.exitCode = 1;
});
