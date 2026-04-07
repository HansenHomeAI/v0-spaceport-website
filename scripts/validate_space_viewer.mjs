import { chromium, webkit } from "playwright";
import { execFile } from "node:child_process";
import fs from "node:fs/promises";
import path from "node:path";
import { promisify } from "node:util";

const targetUrl = process.env.TARGET_URL;
const logsDir = process.env.LOGS_DIR || path.resolve("logs");
const execFileAsync = promisify(execFile);
const iframeSelector =
  'iframe[title="SuperSplat Viewer"], iframe[title="Spaceport SuperSplat Viewer"]';

if (!targetUrl) {
  console.error("TARGET_URL is required");
  process.exit(1);
}

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

async function sampleCanvasLuminance(frame) {
  return frame.evaluate(async () => {
    const wait = (ms) => new Promise((resolve) => window.setTimeout(resolve, ms));
    await wait(1500);

    const canvas = document.querySelector("canvas");
    if (!(canvas instanceof HTMLCanvasElement)) {
      return null;
    }

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

    for (let i = 0; i < image.data.length; i += 4) {
      const r = image.data[i];
      const g = image.data[i + 1];
      const b = image.data[i + 2];
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

async function findBestCanvasLuminance(page, frame) {
  let bestSample = await sampleCanvasLuminance(frame);
  const canvas = frame.locator("canvas");
  const dragDeltas = [260, -260, 420, -420];

  for (const deltaY of dragDeltas) {
    const box = await canvas.boundingBox();
    if (!box) {
      break;
    }

    const centerX = box.x + box.width / 2;
    const centerY = box.y + box.height / 2;
    const targetY = Math.max(box.y + 12, Math.min(box.y + box.height - 12, centerY + deltaY));

    await page.mouse.move(centerX, centerY);
    await page.mouse.down();
    await page.mouse.move(centerX, targetY, { steps: 12 });
    await page.mouse.up();
    await page.waitForTimeout(1200);

    const sample = await sampleCanvasLuminance(frame);
    if (!bestSample || (sample && sample.avgLuminance > bestSample.avgLuminance)) {
      bestSample = sample;
    }
    if (sample && sample.avgLuminance > 8 && sample.nonBlackRatio > 0.1) {
      return sample;
    }
  }

  return bestSample;
}

async function sampleImageLuminance(imagePath, crop, threshold = 8) {
  const { stdout: avgOutput } = await execFileAsync("magick", [
    imagePath,
    "-crop",
    crop,
    "-colorspace",
    "Gray",
    "-format",
    "%[fx:mean*255]",
    "info:",
  ]);
  const { stdout: thresholdOutput } = await execFileAsync("magick", [
    imagePath,
    "-crop",
    crop,
    "-colorspace",
    "Gray",
    "-threshold",
    String(threshold),
    "-format",
    "%[fx:mean]",
    "info:",
  ]);

  return {
    avgLuminance: Number.parseFloat(avgOutput.trim()),
    nonBlackRatio: Number.parseFloat(thresholdOutput.trim()),
  };
}

async function sampleSkyboxZenith(frame, skyboxUrl) {
  return frame.evaluate(async (url) => {
    const loadImage = () =>
      new Promise((resolve, reject) => {
        const image = new Image();
        image.crossOrigin = "anonymous";
        image.onload = () => resolve(image);
        image.onerror = () => reject(new Error(`Failed to load skybox image: ${url}`));
        image.src = url;
      });

    const image = await loadImage();
    const width = image.naturalWidth || image.width;
    const height = image.naturalHeight || image.height;
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

    ctx.drawImage(image, 0, 0);

    const sampleHeight = Math.max(1, Math.floor(height * 0.1));
    const zenithSample = ctx.getImageData(0, 0, width, sampleHeight);

    let luminanceSum = 0;
    let saturationSum = 0;
    let nonBlackPixels = 0;
    const pixelCount = zenithSample.data.length / 4;

    for (let i = 0; i < zenithSample.data.length; i += 4) {
      const r = zenithSample.data[i] / 255;
      const g = zenithSample.data[i + 1] / 255;
      const b = zenithSample.data[i + 2] / 255;
      const luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b;
      luminanceSum += luminance * 255;
      saturationSum += Math.max(r, g, b) - Math.min(r, g, b);
      if ((luminance * 255) > 8) {
        nonBlackPixels += 1;
      }
    }

    return {
      width,
      height,
      sampleHeight,
      avgLuminance: pixelCount ? luminanceSum / pixelCount : 0,
      avgSaturation: pixelCount ? saturationSum / pixelCount : 0,
      nonBlackRatio: pixelCount ? nonBlackPixels / pixelCount : 0,
    };
  }, skyboxUrl);
}

async function dragViewerVertically(page, frame, deltaY) {
  const canvas = frame.locator("canvas");
  const box = await canvas.boundingBox();
  if (!box) {
    throw new Error("Could not locate the viewer canvas for pose capture");
  }

  const centerX = box.x + box.width / 2;
  const centerY = box.y + box.height / 2;
  const targetY = Math.max(box.y + 12, Math.min(box.y + box.height - 12, centerY + deltaY));

  await page.mouse.move(centerX, centerY);
  await page.mouse.down();
  await page.mouse.move(centerX, targetY, { steps: 16 });
  await page.mouse.up();
  await page.waitForTimeout(1200);
}

async function capturePoseScreenshots(page, frame, scenarioName) {
  const poses = [
    { name: "horizon", deltaY: 0 },
    { name: "plus30", deltaY: 140 },
    { name: "plus60", deltaY: 140 },
    { name: "zenith", deltaY: 180 },
  ];
  const screenshotPaths = {};

  for (const pose of poses) {
    if (pose.deltaY !== 0) {
      await dragViewerVertically(page, frame, pose.deltaY);
    }
    const screenshotPath = path.join(logsDir, `space-viewer-${scenarioName}-${pose.name}.png`);
    await page.screenshot({ path: screenshotPath, fullPage: true });
    screenshotPaths[pose.name] = screenshotPath;
  }

  return screenshotPaths;
}

async function runScenario({ name, launcher, options }) {
  const browser = await launcher.launch();
  const context = await browser.newContext(options);
  const page = await context.newPage();
  const consoleLines = [];

  page.on("console", (msg) => {
    consoleLines.push(`[${msg.type()}] ${msg.text()}`);
  });

  const screenshotPath = path.join(logsDir, `space-viewer-${name}.png`);
  const consolePath = path.join(logsDir, `space-viewer-${name}-console.log`);

  try {
    await page.goto(targetUrl, { waitUntil: "domcontentloaded", timeout: 120000 });
    await page.waitForSelector(iframeSelector, { timeout: 15000 });

    const iframeLocator = page.locator(iframeSelector).first();
    const iframeSrc = await iframeLocator.getAttribute("src");
    if (!iframeSrc || !iframeSrc.includes("content=")) {
      throw new Error(`Expected iframe src to include bundle content query param, got: ${iframeSrc}`);
    }

    let frame = null;
    for (let attempt = 0; attempt < 180; attempt += 1) {
      const candidate = page.frames().find((entry) => entry.url().includes("/supersplat-viewer/index.html"));
      if (candidate) {
        try {
          const isReady = await candidate.evaluate(
            () => Boolean(window.sse?.config?.skyboxUrl) && Boolean(document.querySelector("canvas")),
          );
          if (isReady) {
            frame = candidate;
            break;
          }
        } catch {
          // Ignore detached frame handles while the page remounts the viewer iframe.
        }
      }
      await page.waitForTimeout(1000);
    }
    if (!frame) {
      throw new Error("Could not resolve a ready SuperSplat frame with a skybox");
    }

    const skyboxUrl = await frame.evaluate(() => window.sse?.config?.skyboxUrl ?? null);
    await findBestCanvasLuminance(page, frame);
    const zenithSkyboxSample = skyboxUrl ? await sampleSkyboxZenith(frame, skyboxUrl) : null;

    if (!skyboxUrl) {
      throw new Error("Embedded viewer did not receive a skyboxUrl");
    }
    const poseScreenshots = await capturePoseScreenshots(page, frame, name);
    await page.screenshot({ path: screenshotPath, fullPage: true });
    const luminanceSample = await sampleImageLuminance(screenshotPath, "100%x20%+0+0");
    await fs.writeFile(consolePath, consoleLines.join("\n"), "utf8");

    if (luminanceSample.avgLuminance <= 8 || luminanceSample.nonBlackRatio <= 0.1) {
      throw new Error(
        `Skybox validation failed: avgLuminance=${luminanceSample.avgLuminance}, nonBlackRatio=${luminanceSample.nonBlackRatio}`,
      );
    }
    if (!zenithSkyboxSample) {
      throw new Error("Could not sample the uploaded skybox image");
    }
    if (zenithSkyboxSample.avgLuminance <= 8 || zenithSkyboxSample.nonBlackRatio <= 0.1) {
      throw new Error(
        `Skybox zenith validation failed: avgLuminance=${zenithSkyboxSample.avgLuminance}, nonBlackRatio=${zenithSkyboxSample.nonBlackRatio}`,
      );
    }

    return { name, iframeSrc, skyboxUrl, luminanceSample, zenithSkyboxSample, screenshotPath, poseScreenshots, consolePath };
  } finally {
    await page.screenshot({ path: screenshotPath, fullPage: true }).catch(() => {});
    await fs.writeFile(consolePath, consoleLines.join("\n"), "utf8").catch(() => {});
    await browser.close();
  }
}

await fs.mkdir(logsDir, { recursive: true });

const results = [];
for (const scenario of scenarios) {
  const result = await runScenario(scenario);
  results.push(result);
  console.log(
    `✓ ${scenario.name} avgLuminance=${result.luminanceSample.avgLuminance.toFixed(2)} nonBlackRatio=${result.luminanceSample.nonBlackRatio.toFixed(3)} zenithSaturation=${result.zenithSkyboxSample.avgSaturation.toFixed(3)}`,
  );
}

const summaryPath = path.join(logsDir, "space-viewer-validation-results.json");
await fs.writeFile(summaryPath, JSON.stringify({ targetUrl, results }, null, 2));
console.log(`Results saved to ${summaryPath}`);
