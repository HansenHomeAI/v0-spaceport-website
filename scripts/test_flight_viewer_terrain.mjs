#!/usr/bin/env node
/**
 * Flight Viewer Terrain Test
 * Validates the 3D flight viewer workflow using the Playwright MCP server.
 */

import { existsSync } from 'fs';
import { resolve } from 'path';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { SSEClientTransport } from '@modelcontextprotocol/sdk/client/sse.js';

const MCP_URL = process.env.PLAYWRIGHT_MCP_SSE_URL ?? 'http://localhost:5174/sse';
const PREVIEW_BASE = process.env.PREVIEW_URL
  ?? process.env.PLAYWRIGHT_PREVIEW_URL
  ?? process.env.SPACEPORT_PREVIEW_URL
  ?? 'http://localhost:3000';
const FLIGHT_VIEWER_URL = `${PREVIEW_BASE.replace(/\/$/, '')}/flight-viewer`;
const CSV_PATH = resolve(process.env.FLIGHT_VIEWER_CSV ?? 'Edgewood-1.csv');

const client = new Client(
  { name: 'flight-viewer-terrain-test', version: '1.0.0' },
  { capabilities: {} }
);

const transport = new SSEClientTransport(new URL(MCP_URL));
const steps = [];

function record(step, status, info = '') {
  steps.push({ step, status, info });
  const tag = status === 'pass' ? '✅' : status === 'warn' ? '⚠️' : '❌';
  const suffix = info ? ` — ${info}` : '';
  console.log(`${tag} ${step}${suffix}`);
}

function extractText(result) {
  return result?.content?.find((c) => c.type === 'text')?.text ?? '';
}

function extractSnapshot(result) {
  const text = extractText(result);
  const match = text.match(/Page Snapshot:\n```yaml\n([\s\S]*?)```/);
  return match ? match[1] : '';
}

function findUploadRef(snapshot) {
  const uploadPattern = /- generic \[ref=(e\d+)\] \[cursor=pointer\]:\n\s+- generic \[ref=e\d+\]: Add flight files/;
  const match = snapshot.match(uploadPattern);
  return match?.[1] ?? null;
}

async function callTool(name, args, { expectSnapshot = false } = {}) {
  const result = await client.callTool({ name, arguments: args });
  if (expectSnapshot && !extractSnapshot(result)) {
    throw new Error(`${name} did not return a snapshot`);
  }
  return result;
}

async function main() {
  if (!existsSync(CSV_PATH)) {
    throw new Error(`CSV fixture not found at ${CSV_PATH}`);
  }

  await client.connect(transport);
  record('Connect to Playwright MCP', 'pass', `via ${MCP_URL}`);

  const navigateResult = await callTool('browser_navigate', { url: FLIGHT_VIEWER_URL }, { expectSnapshot: true });
  const initialSnapshot = extractSnapshot(navigateResult);
  record('Navigate to flight viewer', 'pass', FLIGHT_VIEWER_URL);

  const uploadRef = findUploadRef(initialSnapshot);
  if (!uploadRef) {
    throw new Error('Could not locate upload dropzone in snapshot');
  }

  await callTool('browser_click', { element: 'Flight files upload area', ref: uploadRef });
  record('Open file chooser', 'pass');

  await callTool('browser_file_upload', { paths: [CSV_PATH] });
  record('Upload Edgewood-1.csv', 'pass', CSV_PATH);

  await callTool('browser_wait_for', { text: 'Loaded Flights', time: 5 });
  const afterUpload = await callTool('browser_snapshot', {}, { expectSnapshot: true });
  record('Render flight overlay', 'pass');

  const consoleLogs = extractText(await callTool('browser_console_messages', {}));
  const hasError = /\b(error|failed)\b/i.test(consoleLogs);
  record('Inspect console logs', hasError ? 'warn' : 'pass', hasError ? 'Errors detected in console output' : 'No errors reported');

  const screenshot = await callTool('browser_take_screenshot', {});
  const screenshotSaved = screenshot?.content?.some((entry) => entry.type === 'image');
  record('Capture screenshot', screenshotSaved ? 'pass' : 'warn');

  console.log('\nTest summary:');
  for (const step of steps) {
    console.log(`- ${step.step}: ${step.status}`);
  }
}

main()
  .catch((error) => {
    record('Flight viewer terrain test failed', 'fail', error.message);
    process.exitCode = 1;
  })
  .finally(async () => {
    await client.close().catch(() => {});
  });
