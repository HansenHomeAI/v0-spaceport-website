/**
 * Build a side-by-side PNG panel (left=input, right=render) using Playwright.
 *
 * Usage:
 *   cd web
 *   MD1_LEFT_IMAGE="../logs/input.jpg" \
 *   MD1_RIGHT_IMAGE="../logs/render.png" \
 *   MD1_PANEL_OUT="../logs/panel.png" \
 *   node scripts/make-md1-side-by-side-panel.mjs
 */

import { chromium } from "playwright";
import fs from "node:fs/promises";
import path from "node:path";

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function mimeTypeForPath(filePath) {
  const ext = path.extname(filePath).toLowerCase();
  if (ext === ".png") return "image/png";
  if (ext === ".jpg" || ext === ".jpeg") return "image/jpeg";
  if (ext === ".webp") return "image/webp";
  return "application/octet-stream";
}

async function toDataUrl(filePath) {
  const bytes = await fs.readFile(filePath);
  const base64 = Buffer.from(bytes).toString("base64");
  return `data:${mimeTypeForPath(filePath)};base64,${base64}`;
}

const leftPath = process.env.MD1_LEFT_IMAGE ?? "";
const rightPath = process.env.MD1_RIGHT_IMAGE ?? "";
const outPath = process.env.MD1_PANEL_OUT ?? "";
const width = Number.parseInt(process.env.MD1_PANEL_WIDTH ?? "2880", 10);
const height = Number.parseInt(process.env.MD1_PANEL_HEIGHT ?? "960", 10);

assert(leftPath, "MD1_LEFT_IMAGE is required");
assert(rightPath, "MD1_RIGHT_IMAGE is required");
assert(outPath, "MD1_PANEL_OUT is required");
assert(Number.isFinite(width) && width > 0, "MD1_PANEL_WIDTH must be a positive integer");
assert(Number.isFinite(height) && height > 0, "MD1_PANEL_HEIGHT must be a positive integer");

await fs.mkdir(path.dirname(outPath), { recursive: true });

const [leftDataUrl, rightDataUrl] = await Promise.all([toDataUrl(leftPath), toDataUrl(rightPath)]);

const html = `<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <style>
      html, body { margin: 0; padding: 0; width: 100%; height: 100%; background: #000; }
      .row { display: flex; flex-direction: row; width: 100vw; height: 100vh; }
      .cell { flex: 1 1 50%; position: relative; overflow: hidden; background: #000; }
      img { width: 100%; height: 100%; object-fit: cover; display: block; }
    </style>
  </head>
  <body>
    <div class="row">
      <div class="cell"><img id="left" src="${leftDataUrl}" alt="input" /></div>
      <div class="cell"><img id="right" src="${rightDataUrl}" alt="render" /></div>
    </div>
  </body>
</html>`;

const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage({ viewport: { width, height } });
  await page.setContent(html, { waitUntil: "load" });
  await page.waitForFunction(() => Array.from(document.images).every((img) => img.complete));
  await page.screenshot({ path: outPath, fullPage: false });
  console.log(`OK ${outPath}`);
} finally {
  await browser.close();
}

