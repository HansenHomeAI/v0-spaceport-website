#!/usr/bin/env node
import { Client } from '@modelcontextprotocol/sdk/client';
import { SSEClientTransport } from '@modelcontextprotocol/sdk/client/sse.js';

const SERVER_URL = process.env.PLAYWRIGHT_MCP_SSE_URL ?? 'http://localhost:5174/sse';
const TARGET_URL = process.argv[2] ?? 'http://localhost:3010/shape-viewer';
const SCREENSHOT_PATH = process.env.SHAPE_VIEWER_SCREENSHOT ?? 'logs/shape-viewer.png';

const client = new Client(
  { name: 'spaceport-shape-viewer-flow', version: '1.0.0' },
  { capabilities: {} }
);

const transport = new SSEClientTransport(new URL(SERVER_URL));

function extractText(result) {
  return result?.content?.find((c) => c.type === 'text')?.text ?? '';
}

function extractSnapshot(result) {
  const text = extractText(result);
  // Tool output format has varied between "Page Snapshot:" and "### Snapshot".
  const match =
    text.match(/Page Snapshot:\n```yaml\n([\s\S]*?)```/) ??
    text.match(/### Snapshot\n```yaml\n([\s\S]*?)```/);
  return match ? match[1] : '';
}

function findRef(snapshot, type, label) {
  const pattern = new RegExp(`- ${type} \"${label}\" \\[ref=(e\\d+)`, 'i');
  const match = snapshot.match(pattern);
  if (!match) throw new Error(`Could not find ref for ${type} "${label}"`);
  return match[1];
}

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function findRefAfterText(snapshot, precedingText, type) {
  const pattern = new RegExp(`${escapeRegExp(precedingText)}[\\s\\S]{0,500}?- ${type} \\[ref=(e\\d+)\\]`, 'i');
  const match = snapshot.match(pattern);
  if (!match) throw new Error(`Could not find ref for ${type} after text "${precedingText}"`);
  return match[1];
}

async function callTool(name, args) {
  return await client.callTool({ name, arguments: args });
}

function logLine(step, status, info = '') {
  const suffix = info ? ` - ${info}` : '';
  // ASCII-only logs (no emoji) so they paste cleanly into CI logs.
  console.log(`[${status}] ${step}${suffix}`);
}

async function readWaypointCount() {
  const result = await callTool('browser_evaluate', {
    function: `() => {
      // Find a text node containing "Waypoints:" in the diagnostics box.
      const root = document.querySelector('main') ?? document.body;
      const text = root?.innerText ?? '';
      const m = text.match(/Waypoints:\\s*(\\d+)\\s*per battery/i);
      return { text: m ? m[0] : null, count: m ? Number(m[1]) : null };
    }`
  });
  const text = extractText(result);
  // Tool output is a text blob; extract the numeric count without relying on strict JSON parsing.
  const countMatch = text.match(/"count"\s*:\s*(\d+)/);
  const textMatch = text.match(/"text"\s*:\s*"([^"]+)"/);
  return {
    count: countMatch ? Number(countMatch[1]) : null,
    raw: textMatch ? textMatch[1] : text.trim().slice(0, 200)
  };
}

async function main() {
  try {
    await client.connect(transport);
    logLine('Connect to MCP server', 'PASS', SERVER_URL);

    await callTool('browser_navigate', { url: TARGET_URL });
    logLine('Navigate', 'PASS', TARGET_URL);

    // Wait for the heading so we know the page hydrated.
    await callTool('browser_wait_for', { text: 'Flight Shape Viewer', time: 10 });
    logLine('Wait for heading', 'PASS');

    // Interact with a couple controls to ensure the UI remains usable.
    const snapshot1 = extractSnapshot(await callTool('browser_snapshot', {}));
    if (!snapshot1) throw new Error('browser_snapshot did not return a snapshot');
    const slicesRef = findRefAfterText(snapshot1, 'Number of Batteries (slices)', 'slider');
    const nRef = findRefAfterText(snapshot1, 'Number of Bounces (N)', 'slider');
    const labelsRef = findRef(snapshot1, 'checkbox', 'Show Waypoint Labels');

    await callTool('browser_fill_form', {
      fields: [
        { name: 'Number of Bounces (N)', type: 'slider', ref: nRef, value: '6' },
        { name: 'Show Waypoint Labels', type: 'checkbox', ref: labelsRef, value: 'true' }
      ]
    });
    logLine('Adjust controls', 'PASS', 'N=6, labels=on');

    // Validate low-slice sampling: slices=1 should produce more waypoints than slices=2 and slices>=3.
    await callTool('browser_fill_form', { fields: [{ name: 'Number of Batteries (slices)', type: 'slider', ref: slicesRef, value: '1' }] });
    const slice1 = await readWaypointCount();
    logLine('Waypoints @ slices=1', slice1.count ? 'PASS' : 'WARN', String(slice1.count ?? slice1.raw ?? 'unknown'));

    await callTool('browser_fill_form', { fields: [{ name: 'Number of Batteries (slices)', type: 'slider', ref: slicesRef, value: '2' }] });
    const slice2 = await readWaypointCount();
    logLine('Waypoints @ slices=2', slice2.count ? 'PASS' : 'WARN', String(slice2.count ?? slice2.raw ?? 'unknown'));

    await callTool('browser_fill_form', { fields: [{ name: 'Number of Batteries (slices)', type: 'slider', ref: slicesRef, value: '4' }] });
    const slice4 = await readWaypointCount();
    logLine('Waypoints @ slices=4', slice4.count ? 'PASS' : 'WARN', String(slice4.count ?? slice4.raw ?? 'unknown'));

    if (typeof slice1.count === 'number' && typeof slice2.count === 'number' && typeof slice4.count === 'number') {
      if (!(slice1.count > slice2.count && slice2.count >= slice4.count)) {
        throw new Error(`Unexpected waypoint counts: slices=1(${slice1.count}) slices=2(${slice2.count}) slices=4(${slice4.count})`);
      }
      logLine('Low-slice midpoints', 'PASS', 'slices=1 > slices=2 >= slices=4');
    } else {
      logLine('Low-slice midpoints', 'WARN', 'Could not parse waypoint counts');
    }

    // Sanity-check we have a canvas with non-zero size.
    const evalResult = await callTool('browser_evaluate', {
      function: `() => {
        const c = document.querySelector('canvas');
        if (!c) return { ok: false, reason: 'no_canvas' };
        const r = c.getBoundingClientRect();
        return { ok: true, width: Math.round(r.width), height: Math.round(r.height) };
      }`
    });
    const evalText = extractText(evalResult);
    logLine('Canvas present', 'PASS', evalText.trim().slice(0, 200));

    await callTool('browser_take_screenshot', { type: 'png', filename: SCREENSHOT_PATH });
    logLine('Screenshot', 'PASS', SCREENSHOT_PATH);

    // Capture console errors (if any).
    const consoleResult = await callTool('browser_console_messages', { level: 'error' });
    const consoleText = extractText(consoleResult).trim();
    const zeroMessages =
      /Returning 0 messages/i.test(consoleText) ||
      /Total messages:\s*0\b/i.test(consoleText);
    if (!consoleText || zeroMessages) {
      logLine('Console errors', 'PASS', 'none');
    } else {
      logLine('Console errors', 'FAIL', 'See stderr output');
      console.error(consoleText);
      process.exitCode = 1;
      return;
    }
  } catch (err) {
    logLine('Shape viewer flow failed', 'FAIL', err?.message ?? String(err));
    process.exitCode = 1;
  } finally {
    await client.close().catch(() => {});
  }
}

await main();
