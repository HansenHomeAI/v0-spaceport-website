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
  "https://spaceport-ml-processing.s3.amazonaws.com/public-viewer/sogs-test-1753999934/meta.json";

const previewUrl = process.env.SOGS_VIEWER_URL ?? DEFAULT_PREVIEW;
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

const inputSelector = "#sogs-url-input";
const submitSelector = 'button[type="submit"]';
const iframeSelector = 'iframe[title="SuperSplat Viewer"]';

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
    const frameLocator = page.frameLocator(iframeSelector);
    await frameLocator.locator("#loadingWrap.hidden").waitFor({ timeout: 360000 });
    await page.waitForSelector('text=SOGS bundle loaded in the embedded viewer.', { timeout: 360000 });

    await page.screenshot({ path: screenshotPath, fullPage: true });
    await fs.writeFile(consolePath, consoleBuffer.join("\n"), "utf8");
    return { name, screenshotPath, consolePath };
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

  for (const scenario of scenarios) {
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
