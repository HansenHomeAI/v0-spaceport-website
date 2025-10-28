#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import process from 'node:process';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { SSEClientTransport } from '@modelcontextprotocol/sdk/client/sse.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, '..');

const SERVER_URL = process.env.PLAYWRIGHT_MCP_SSE_URL ?? 'http://localhost:5174/sse';
const TARGET_URL = process.env.FLIGHT_VIEWER_URL ?? 'http://localhost:3004/flight-viewer';
const CSV_PATH = process.env.FLIGHT_VIEWER_CSV ?? path.resolve(repoRoot, 'Edgewood-1.csv');
const OUTPUT_DIR = path.resolve(repoRoot, 'logs');
const OUTPUT_PREFIX = process.env.FLIGHT_VIEWER_OUTPUT_PREFIX ?? 'flight-viewer-baseline';
const SCREENSHOT_NAME = `${OUTPUT_PREFIX}.png`;
const METRICS_NAME = `${OUTPUT_PREFIX}.json`;

function ensureFileExists(filePath) {
  if (!fs.existsSync(filePath)) {
    throw new Error(`Required file missing: ${filePath}`);
  }
}

function extractText(result) {
  return result?.content?.find((item) => item.type === 'text')?.text ?? '';
}

function extractImageBase64(result) {
  const image = result?.content?.find((item) => item.type === 'image');
  return image?.data ?? null;
}

function extractJsonBlock(text) {
  const match = text.match(/### Result\n([\s\S]*?)\n\n###/);
  if (!match) {
    throw new Error('Unable to extract JSON block from result');
  }
  return JSON.parse(match[1]);
}

function extractSnapshot(text) {
  const match = text.match(/```yaml\n([\s\S]*?)```/);
  if (!match) {
    throw new Error('Snapshot YAML not found in result');
  }
  return match[1];
}

function findRefForText(snapshotYaml, needle) {
  const lines = snapshotYaml.split('\n');
  for (let i = 0; i < lines.length; i += 1) {
    if (lines[i].includes(needle)) {
      for (let j = i - 1; j >= 0; j -= 1) {
        const refMatch = lines[j].match(/\[ref=(e\d+)\]/);
        if (refMatch) {
          return refMatch[1];
        }
      }
    }
  }
  throw new Error(`Reference not found for text: ${needle}`);
}

async function main() {
  ensureFileExists(CSV_PATH);
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });

  const client = new Client({ name: 'flight-viewer-baseline', version: '1.0.0' }, { capabilities: {} });
  const transport = new SSEClientTransport(new URL(SERVER_URL));

  try {
    await client.connect(transport);
    console.log(`✅ Connected to Playwright MCP at ${SERVER_URL}`);

    await client.callTool({ name: 'browser_resize', arguments: { width: 1400, height: 1100 } });
    console.log('🖥️  Viewport resized to 1400x1100');

    await client.callTool({ name: 'browser_navigate', arguments: { url: TARGET_URL } });
    console.log(`🌐 Navigated to ${TARGET_URL}`);

    await client.callTool({ name: 'browser_wait_for', arguments: { time: 2 } });

    const initialSnapshot = await client.callTool({ name: 'browser_snapshot', arguments: {} });
    const snapshotText = extractSnapshot(extractText(initialSnapshot));
    const uploadRef = findRefForText(snapshotText, 'Add flight files');
    console.log(`📍 Upload area ref: ${uploadRef}`);

    await client.callTool({ name: 'browser_click', arguments: { element: 'flight upload control', ref: uploadRef } });
    console.log('🖱️  Clicked flight upload control');

    await client.callTool({ name: 'browser_file_upload', arguments: { paths: [CSV_PATH] } });
    console.log(`📤 Uploaded file: ${CSV_PATH}`);

    await client.callTool({ name: 'browser_wait_for', arguments: { time: 5 } });

    const metricsResult = await client.callTool({
      name: 'browser_evaluate',
      arguments: {
        function: `() => {
          const container = document.querySelector('.flight-viewer__cesium-canvas');
          const viewer = document.querySelector('.cesium-viewer');
          const widget = document.querySelector('.cesium-widget');
          const canvases = Array.from(document.querySelectorAll('.cesium-widget canvas'));
          return {
            timestamp: new Date().toISOString(),
            containerClientHeight: container?.clientHeight ?? null,
            containerBoundingHeight: container ? Math.round(container.getBoundingClientRect().height) : null,
            viewerClientHeight: viewer?.clientHeight ?? null,
            viewerInlineHeight: viewer?.style?.height ?? null,
            widgetClientHeight: widget?.clientHeight ?? null,
            widgetInlineHeight: widget?.style?.height ?? null,
            canvasClientHeights: canvases.map((c) => c.clientHeight),
            canvasHeightsAttr: canvases.map((c) => c.height),
            canvasStyles: canvases.map((c) => c.getAttribute('style')),
            notes: 'Baseline measurement prior to fix'
          };
        }`
      }
    });

    const metricsText = extractText(metricsResult);
    const metrics = extractJsonBlock(metricsText);
    console.log('📏 Baseline metrics:', metrics);

    fs.writeFileSync(path.join(OUTPUT_DIR, METRICS_NAME), JSON.stringify(metrics, null, 2));
    console.log(`📝 Saved metrics to ${METRICS_NAME}`);

    const screenshotResult = await client.callTool({
      name: 'browser_take_screenshot',
      arguments: { filename: `logs/${SCREENSHOT_NAME}` }
    });

    const imageBase64 = extractImageBase64(screenshotResult);
    if (imageBase64) {
      fs.writeFileSync(path.join(OUTPUT_DIR, SCREENSHOT_NAME), Buffer.from(imageBase64, 'base64'));
      console.log(`📸 Saved screenshot to ${SCREENSHOT_NAME}`);
    } else {
      console.warn('⚠️  Screenshot base64 not found in result; skipping save');
    }

  } finally {
    await client.close().catch(() => {});
  }
}

main().catch((error) => {
  console.error('❌ Baseline run failed:', error);
  process.exitCode = 1;
});
