#!/usr/bin/env node
import { Client } from '@modelcontextprotocol/sdk/client';
import { SSEClientTransport } from '@modelcontextprotocol/sdk/client/sse.js';

const SERVER_URL = process.env.PLAYWRIGHT_MCP_SSE_URL ?? 'http://localhost:5174/sse';
const BASE_URL = process.env.PREVIEW_URL;

if (!BASE_URL) {
  console.error('PREVIEW_URL is required.');
  process.exit(1);
}

const PRICING_URL = new URL('/pricing', BASE_URL).toString();

const client = new Client(
  { name: 'spaceport-pricing-smoke', version: '1.0.0' },
  { capabilities: {} }
);

const transport = new SSEClientTransport(new URL(SERVER_URL));
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
  const match = extractText(result).match(/Page Snapshot:\n```yaml\n([\s\S]*?)```/);
  return match ? match[1] : '';
}

async function callTool(name, args, { expectSnapshot = false } = {}) {
  const result = await client.callTool({ name, arguments: args });
  if (expectSnapshot && !extractSnapshot(result)) {
    throw new Error(`${name} did not return a snapshot`);
  }
  return result;
}

function assertSnapshot(snapshot, label, pattern) {
  if (pattern.test(snapshot)) {
    record(label, 'pass');
    return true;
  }
  record(label, 'fail', `Missing ${pattern}`);
  return false;
}

async function main() {
  try {
    await client.connect(transport);
    record('Connect to MCP server', 'pass', `via ${SERVER_URL}`);

    const navigate = await callTool('browser_navigate', { url: PRICING_URL }, { expectSnapshot: true });
    const snapshot = extractSnapshot(navigate);
    record('Navigate to pricing page', 'pass', PRICING_URL);

    const expectations = [
      ['See per-model tier', /Per model\./i],
      ['See upfront price', /\$599 upfront/i],
      ['See hosting price', /\$29\/mo hosting/i],
      ['See first month free note', /First month free/i],
      ['See enterprise tier', /Enterprise\./i],
      ['See contact link', /link "Contact"/i]
    ];

    const failures = expectations
      .map(([label, pattern]) => assertSnapshot(snapshot, label, pattern))
      .filter((result) => !result).length;

    if (failures > 0) {
      record('Pricing snapshot validation', 'fail', `${failures} checks failed`);
      process.exitCode = 1;
    } else {
      record('Pricing snapshot validation', 'pass');
    }
  } catch (error) {
    record('Pricing smoke test failed', 'fail', error.message);
    process.exitCode = 1;
  } finally {
    await client.close().catch(() => {});
  }
}

await main();
