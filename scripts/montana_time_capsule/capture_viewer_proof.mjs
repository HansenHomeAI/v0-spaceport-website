#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';

import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { SSEClientTransport } from '@modelcontextprotocol/sdk/client/sse.js';

function readText(filePath) {
  return fs.readFileSync(filePath, 'utf8').trim();
}

function isoStamp() {
  return new Date().toISOString().replace(/[-:]/g, '').replace(/\..*$/, 'Z');
}

async function main() {
  const repoRoot = process.cwd();
  const stamp = isoStamp();

  const defaultSkyUrlFile =
    'logs/montana-time-capsule/viewer-sky-url-friday-mtc-20260524T0001Z-20260524T132658Z.txt';
  const defaultNoSkyUrlFile =
    'logs/montana-time-capsule/viewer-nosky-url-friday-mtc-20260524T0001Z-20260524T132658Z.txt';

  const skyUrl = process.argv[2] ?? readText(path.join(repoRoot, defaultSkyUrlFile));
  const noSkyUrl = process.argv[3] ?? readText(path.join(repoRoot, defaultNoSkyUrlFile));

  const outDir = path.join(repoRoot, 'logs/montana-time-capsule');
  fs.mkdirSync(outDir, { recursive: true });

  const toolsOut = path.join(outDir, `playwright-mcp-tools-${stamp}.json`);
  const skyPng = path.join(outDir, `viewer-proof-friday-mtc-20260524T0001Z-sky-${stamp}.png`);
  const noSkyPng = path.join(outDir, `viewer-proof-friday-mtc-20260524T0001Z-nosky-${stamp}.png`);
  const consoleOut = path.join(outDir, `viewer-proof-console-${stamp}.txt`);

  const serverUrl = process.env.PLAYWRIGHT_MCP_SSE_URL ?? 'http://localhost:5174/sse';
  const client = new Client({ name: 'mtc-viewer-proof', version: '1.0.0' }, { capabilities: {} });

  try {
    await client.connect(new SSEClientTransport(new URL(serverUrl)));

    const toolList = await client.listTools();
    fs.writeFileSync(toolsOut, JSON.stringify(toolList, null, 2));

    await client.callTool({ name: 'browser_resize', arguments: { width: 1280, height: 720 } });

    await client.callTool({ name: 'browser_navigate', arguments: { url: skyUrl } });
    await client.callTool({ name: 'browser_wait_for', arguments: { time: 12 } });
    await client.callTool({
      name: 'browser_take_screenshot',
      arguments: { type: 'png', filename: path.relative(repoRoot, skyPng), fullPage: true }
    });

    await client.callTool({ name: 'browser_navigate', arguments: { url: noSkyUrl } });
    await client.callTool({ name: 'browser_wait_for', arguments: { time: 12 } });
    await client.callTool({
      name: 'browser_take_screenshot',
      arguments: { type: 'png', filename: path.relative(repoRoot, noSkyPng), fullPage: true }
    });

    await client.callTool({
      name: 'browser_console_messages',
      arguments: { level: 'info', all: true, filename: path.relative(repoRoot, consoleOut) }
    });

    console.log(`OK tools=${path.relative(repoRoot, toolsOut)}`);
    console.log(`OK sky=${path.relative(repoRoot, skyPng)}`);
    console.log(`OK nosky=${path.relative(repoRoot, noSkyPng)}`);
    console.log(`OK console=${path.relative(repoRoot, consoleOut)}`);
  } finally {
    await client.close().catch(() => {});
  }
}

await main();
