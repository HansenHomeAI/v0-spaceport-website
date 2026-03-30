import fs from "node:fs/promises";
import path from "node:path";
import { chromium } from "playwright";

const defaultEdgeMeta =
  "https://dnzrpn12urol1.cloudfront.net/models/edited-splat-20260330-213120-clean/supersplat_bundle/meta.json";
const targetBase = process.argv[2] ?? "http://127.0.0.1:3010/index.html";
const edgeMeta = process.argv[3] ?? defaultEdgeMeta;
const targetUrl = `${targetBase}?url=${encodeURIComponent(edgeMeta)}`;
const logsDir = path.resolve("logs");
const summaryPath = path.join(logsDir, "sogs-onefile-edge-validation.json");
const screenshotPath = path.join(logsDir, "sogs-onefile-edge-validation.png");

await fs.mkdir(logsDir, { recursive: true });

const requestUrls = [];
const failedRequests = [];
const consoleMessages = [];

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({
  viewport: { width: 1440, height: 960 },
});

page.on("requestfinished", (request) => {
  const url = request.url();
  if (url.includes("dnzrpn12urol1.cloudfront.net") || url.includes("127.0.0.1:3010")) {
    requestUrls.push(url);
  }
});

page.on("requestfailed", (request) => {
  failedRequests.push({
    url: request.url(),
    errorText: request.failure()?.errorText || "unknown",
  });
});

page.on("console", (msg) => {
  consoleMessages.push({
    type: msg.type(),
    text: msg.text(),
  });
});

page.on("pageerror", (error) => {
  consoleMessages.push({
    type: "pageerror",
    text: String(error),
  });
});

function logStep(label) {
  console.log(`[validate] ${label}`);
}

async function waitForRequest(predicate, timeoutMs, label) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (requestUrls.some(predicate)) {
      return;
    }
    await page.waitForTimeout(250);
  }
  throw new Error(`Timed out waiting for ${label}`);
}

async function collectRuntimeState() {
  return page.evaluate(async () => {
    const frame = document.querySelector("iframe.sogs-migrated-iframe");
    const w = frame?.contentWindow;
    const resolvedConfig = await Promise.resolve(w?.sse?.configReady ?? w?.sse?.config ?? null);
    const camera = w?.__sogsCtx?.viewer?.cameraManager?.camera;
    let focus = null;
    try {
      const point = camera?.calcFocusPoint?.();
      if (point) {
        focus = [point.x, point.y, point.z];
      }
    } catch {
      focus = null;
    }
    return {
      hasFrame: Boolean(frame),
      dragReady: w?.__sogsSplatXzDragReady === true,
      hasViewer: Boolean(w?.__sogsCtx?.viewer),
      hasEnvAtlas: Boolean(w?.__sogsCtx?.app?.scene?.envAtlas),
      skyboxUrl: resolvedConfig?.skyboxUrl ?? null,
      contentUrl: resolvedConfig?.contentUrl ?? null,
      camera: camera
        ? {
            position: [camera.position.x, camera.position.y, camera.position.z],
            fov: camera.fov,
            target: focus,
          }
        : null,
    };
  });
}

let summary = {
  ok: false,
  targetUrl,
  runtimeState: null,
  sawMeta: false,
  sawSpaceportBundle: false,
  sawSkybox: false,
  failedRequests: [],
  consoleMessages: [],
  requestSample: [],
  error: null,
};

try {
  logStep(`goto ${targetUrl}`);
  await page.goto(targetUrl, { waitUntil: "domcontentloaded", timeout: 120000 });

  logStep("wait for outer iframe");
  await page.waitForSelector("iframe.sogs-migrated-iframe", { timeout: 120000 });

  logStep("wait for viewer boot");
  await page.waitForFunction(() => {
    const frame = document.querySelector("iframe.sogs-migrated-iframe");
    const w = frame?.contentWindow;
    return Boolean(w && w.__sogsSplatXzDragReady === true && w.__sogsCtx?.viewer?.cameraManager?.camera);
  }, undefined, { timeout: 180000 });

  logStep("wait for bundle metadata and skybox fetches");
  await waitForRequest(
    (url) =>
      url.includes("/supersplat_bundle/spaceport_bundle.json") &&
      url.includes("dnzrpn12urol1.cloudfront.net"),
    60000,
    "spaceport_bundle.json request",
  );

  await waitForRequest(
    (url) =>
      url.includes("/supersplat_bundle/skybox/kloppenheim_06_puresky_equirect.webp") &&
      url.includes("dnzrpn12urol1.cloudfront.net"),
    60000,
    "skybox request",
  );

  logStep("wait for environment atlas");
  await page.waitForFunction(() => {
    const frame = document.querySelector("iframe.sogs-migrated-iframe");
    return Boolean(frame?.contentWindow?.__sogsCtx?.app?.scene?.envAtlas);
  }, undefined, { timeout: 120000 });

  logStep("capture runtime state");
  const runtimeState = await collectRuntimeState();

  logStep("open path panel");
  await page.getByTestId("path-editor-toggle").click({ timeout: 30000 });
  await page.waitForFunction(() => {
    const panel = document.querySelector('[data-testid="animation-path-panel"]');
    return Boolean(panel && panel.classList.contains("active"));
  }, undefined, { timeout: 30000 });

  logStep("tap inside viewer");
  const iframeHandle = await page.$("iframe.sogs-migrated-iframe");
  const iframeBox = await iframeHandle?.boundingBox();
  if (!iframeBox) {
    throw new Error("Viewer iframe bounding box missing");
  }
  await page.mouse.click(iframeBox.x + iframeBox.width * 0.5, iframeBox.y + iframeBox.height * 0.5);
  await page.waitForSelector(".sogs-tap-pick-feedback", { timeout: 30000 });

  logStep("save screenshot");
  await page.screenshot({ path: screenshotPath, fullPage: true });

  summary = {
    ok: true,
    targetUrl,
    runtimeState,
    sawMeta: requestUrls.some((url) => url.includes("/supersplat_bundle/meta.json")),
    sawSpaceportBundle: requestUrls.some((url) => url.includes("/supersplat_bundle/spaceport_bundle.json")),
    sawSkybox: requestUrls.some((url) => url.includes("/supersplat_bundle/skybox/kloppenheim_06_puresky_equirect.webp")),
    failedRequests,
    consoleMessages: consoleMessages.slice(-20),
    requestSample: requestUrls.slice(-20),
    error: null,
  };
} catch (error) {
  summary = {
    ...summary,
    runtimeState: await collectRuntimeState().catch(() => null),
    sawMeta: requestUrls.some((url) => url.includes("/supersplat_bundle/meta.json")),
    sawSpaceportBundle: requestUrls.some((url) => url.includes("/supersplat_bundle/spaceport_bundle.json")),
    sawSkybox: requestUrls.some((url) => url.includes("/supersplat_bundle/skybox/kloppenheim_06_puresky_equirect.webp")),
    failedRequests,
    consoleMessages: consoleMessages.slice(-40),
    requestSample: requestUrls.slice(-40),
    error: error instanceof Error ? error.stack || error.message : String(error),
  };
  throw error;
} finally {
  await fs.writeFile(summaryPath, `${JSON.stringify(summary, null, 2)}\n`, "utf8");
  await page.close().catch(() => {});
  await browser.close().catch(() => {});
  logStep(`summary ${summaryPath}`);
}

console.log(JSON.stringify(summary, null, 2));
