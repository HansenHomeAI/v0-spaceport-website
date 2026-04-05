import { chromium } from "playwright";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, "..", "..");
const logsDir = path.join(repoRoot, "logs");

const DEFAULT_PREVIEW = "https://agent-83927461-sfm-pointcloud-viewer.v0-spaceport-website-preview2.pages.dev";
const DEFAULT_BUNDLE =
  "https://spaceport-ml-processing.s3.amazonaws.com/compressed/sogs-test-1763664401/supersplat_bundle/meta.json";

const previewUrl = process.env.PIPELINE_VIEWER_URL ?? DEFAULT_PREVIEW;
const bundleUrl = process.env.SOGS_BUNDLE_URL ?? DEFAULT_BUNDLE;
const sfmStatusSelector = "text=/Loaded\s+\d+\s+points/";

async function ensureLogsDir() {
  await fs.mkdir(logsDir, { recursive: true });
}

async function run() {
  await ensureLogsDir();
  const consoleBuffer = [];
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1400, height: 900 } });
  const page = await context.newPage();

  page.on("console", (msg) => {
    consoleBuffer.push(`[${msg.type()}] ${msg.text()}`);
  });

  const screenshotPath = path.join(logsDir, "pipeline-viewer.png");
  const consolePath = path.join(logsDir, "pipeline-viewer-console.log");

  try {
    await page.goto(`${previewUrl}/pipeline-viewer`, { waitUntil: "domcontentloaded", timeout: 120000 });
    await page.waitForSelector("text=Pipeline Viewer", { timeout: 15000 });

    const sfmButton = page.getByRole("button", { name: "SfM (COLMAP)" });
    await sfmButton.click();
    await page.waitForSelector(sfmStatusSelector, { timeout: 120000 });

    const sfmCanvas = page.locator("canvas").first();
    const box = await sfmCanvas.boundingBox();
    if (box) {
      await page.mouse.move(box.x + box.width * 0.5, box.y + box.height * 0.5);
      await page.mouse.down();
      await page.mouse.move(box.x + box.width * 0.65, box.y + box.height * 0.45, { steps: 15 });
      await page.mouse.up();
    }

    const compressedButton = page.getByRole("button", { name: "Compressed (SOGS)" });
    await compressedButton.click();

    const compressedInput = page.locator("#supersplat-compressed-sogs");
    if ((await compressedInput.count()) > 0) {
      await compressedInput.fill(bundleUrl);
    }

    const loadButton = page.getByRole("button", { name: "Load Compressed" });
    await loadButton.click();

    await page.waitForSelector('iframe[title="Compressed SOGS Viewer"]', { timeout: 30000 });

    await page.screenshot({ path: screenshotPath, fullPage: true });
    await fs.writeFile(consolePath, consoleBuffer.join("\n"), "utf8");
  } catch (error) {
    await page.screenshot({ path: screenshotPath, fullPage: true }).catch(() => {});
    await fs.writeFile(consolePath, consoleBuffer.join("\n"), "utf8").catch(() => {});
    throw error;
  } finally {
    await browser.close();
  }
}

run().catch((error) => {
  console.error("Pipeline viewer test failed", error);
  process.exitCode = 1;
});
