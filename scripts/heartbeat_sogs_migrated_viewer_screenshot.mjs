#!/usr/bin/env node
import { Client } from '@modelcontextprotocol/sdk/client';
import { SSEClientTransport } from '@modelcontextprotocol/sdk/client/sse.js';

const SERVER_URL = process.env.PLAYWRIGHT_MCP_SSE_URL ?? 'http://localhost:5174/sse';
const TARGET_URL = process.argv[2];
const SCREENSHOT_PATH = process.argv[3];

if (!TARGET_URL || !SCREENSHOT_PATH) {
  console.error('Usage: scripts/heartbeat_sogs_migrated_viewer_screenshot.mjs <url> <png_path>');
  process.exit(2);
}

const client = new Client(
  { name: 'heartbeat-sogs-migrated-viewer-screenshot', version: '1.0.0' },
  { capabilities: {} }
);

const transport = new SSEClientTransport(new URL(SERVER_URL));

function extractText(result) {
  return result?.content?.find((c) => c.type === 'text')?.text ?? '';
}

async function callTool(name, args) {
  return await client.callTool({ name, arguments: args });
}

async function main() {
  await client.connect(transport);

  await callTool('browser_navigate', { url: TARGET_URL });
  await callTool('browser_wait_for', { time: 3000 });

  const readyState = await callTool('browser_evaluate', { function: '() => document.readyState' });
  console.log(`readyState=${extractText(readyState).trim()}`);

  // Let WebGL settle (also catches cases where the page shows a loading spinner indefinitely).
  await callTool('browser_wait_for', { time: 7000 });

  await callTool('browser_take_screenshot', { type: 'png', filename: SCREENSHOT_PATH });
  console.log(`screenshot=${SCREENSHOT_PATH}`);

  const snapshot = await callTool('browser_snapshot', {});
  const snapshotText = extractText(snapshot);
  if (snapshotText) {
    console.log('snapshot_head=' + snapshotText.trim().slice(0, 400).replace(/\s+/g, ' '));
  }
}

main()
  .then(() => process.exit(0))
  .catch((err) => {
    console.error(String(err?.stack ?? err));
    process.exit(1);
  });

