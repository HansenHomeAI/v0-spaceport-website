#!/usr/bin/env node
import { mkdtempSync, rmSync } from "node:fs";
import { readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";

import playwright from "../web/node_modules/playwright/index.js";

const { chromium } = playwright;

const DEFAULT_MANIFEST = "scripts/explore_listings_manifest.json";
const DEFAULT_THUMBNAIL_BASE = "https://spcprt.com/spaces";
const DEFAULT_BUCKET = "spaces-viewers";
const DEFAULT_RENDER_SETTLE_MS = 10000;
const DEFAULT_DELAY_MS = 2000;
const DEFAULT_CACHE_CONTROL = "public, max-age=86400";

function parseArgs(argv) {
  const args = {
    manifest: DEFAULT_MANIFEST,
    thumbnailBaseUrl: DEFAULT_THUMBNAIL_BASE,
    bucket: DEFAULT_BUCKET,
    renderSettleMs: DEFAULT_RENDER_SETTLE_MS,
    delayMs: DEFAULT_DELAY_MS,
    onlyMissing: true,
    slugs: null,
  };

  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === "--manifest") args.manifest = argv[++i];
    else if (arg === "--thumbnail-base-url") args.thumbnailBaseUrl = argv[++i];
    else if (arg === "--bucket") args.bucket = argv[++i];
    else if (arg === "--render-settle-ms") args.renderSettleMs = Number(argv[++i]);
    else if (arg === "--delay-ms") args.delayMs = Number(argv[++i]);
    else if (arg === "--slugs") args.slugs = new Set(argv[++i].split(",").map((value) => value.trim()).filter(Boolean));
    else if (arg === "--all") args.onlyMissing = false;
  }
  return args;
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function normalizeUrl(url) {
  return url.trim().replace(/\/+$/, "");
}

async function headOk(url) {
  const response = await fetch(url, {
    method: "HEAD",
    headers: { "User-Agent": "Mozilla/5.0" },
  }).catch(() => null);
  const contentType = response?.headers.get("content-type") || "";
  return Boolean(response?.ok && contentType.startsWith("image/"));
}

async function renderThumb(page, viewerUrl, outPath, renderSettleMs) {
  await page.goto(viewerUrl, { waitUntil: "domcontentloaded", timeout: 120000 });
  await page.waitForFunction(
    () => {
      const target = document.querySelector("canvas, iframe, model-viewer");
      if (!target) return false;
      const rect = target.getBoundingClientRect();
      return rect.width >= 200 && rect.height >= 150;
    },
    { timeout: 45000 }
  ).catch(() => undefined);
  await sleep(renderSettleMs);
  await page.screenshot({ path: outPath, type: "jpeg", quality: 82 });
}

function uploadToR2(bucket, key, filePath) {
  const result = spawnSync(
    "wrangler",
    [
      "r2",
      "object",
      "put",
      `${bucket}/${key}`,
      "--file",
      filePath,
      "--content-type",
      "image/jpeg",
      "--cache-control",
      DEFAULT_CACHE_CONTROL,
      "--remote",
    ],
    { encoding: "utf8" }
  );
  if (result.status !== 0) {
    throw new Error(result.stderr || result.stdout || "wrangler r2 object put failed");
  }
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const items = JSON.parse(readFileSync(args.manifest, "utf8"));
  const tempDir = mkdtempSync(join(tmpdir(), "explore-thumb-"));
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1200, height: 900 } });
  const results = {
    uploaded: [],
    skipped: [],
    failed: [],
  };

  try {
    for (const item of items) {
      const slug = item.viewerSlug;
      if (args.slugs && !args.slugs.has(slug)) {
        continue;
      }
      const viewerUrl = normalizeUrl(item.viewerUrl);
      const thumbUrl = `${args.thumbnailBaseUrl.replace(/\/+$/, "")}/${slug}/thumb.jpg`;
      if (args.onlyMissing && (await headOk(thumbUrl))) {
        results.skipped.push({ slug, reason: "already-present" });
        continue;
      }

      const outPath = join(tempDir, `${slug}.jpg`);
      try {
        await renderThumb(page, viewerUrl, outPath, args.renderSettleMs);
        uploadToR2(args.bucket, `models/${slug}/thumb.jpg`, outPath);
        const verified = await headOk(thumbUrl);
        if (!verified) {
          throw new Error("thumb upload did not verify publicly");
        }
        results.uploaded.push({ slug, viewerUrl, thumbUrl });
      } catch (error) {
        results.failed.push({
          slug,
          viewerUrl,
          reason: error instanceof Error ? error.message : String(error),
        });
      }

      if (args.delayMs > 0) {
        await sleep(args.delayMs);
      }
    }
  } finally {
    await page.close().catch(() => undefined);
    await browser.close().catch(() => undefined);
    rmSync(tempDir, { recursive: true, force: true });
  }

  process.stdout.write(JSON.stringify(results, null, 2));
  process.stdout.write("\n");
  process.exit(results.failed.length ? 1 : 0);
}

await main();
