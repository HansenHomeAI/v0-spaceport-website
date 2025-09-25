#!/usr/bin/env node
import { Client } from '@modelcontextprotocol/sdk/client';
import { SSEClientTransport } from '@modelcontextprotocol/sdk/client/sse.js';

const SERVER_URL = process.env.PLAYWRIGHT_MCP_SSE_URL ?? 'http://127.0.0.1:5174/sse';
const PREVIEW_URL = process.argv[2] ?? process.env.PREVIEW_URL;
const PLAN = process.argv[3] ?? 'single';

if (!PREVIEW_URL) {
  console.error('Usage: run_subscription_checkout_flow.mjs <preview-url> [plan]');
  process.exit(1);
}

const PLAN_LABELS = {
  single: 'Sign in to Subscribe',
  starter: 'Sign in to Subscribe',
  growth: 'Sign in to Subscribe'
};

const SUCCESS_TEXT = 'Sign in to create your model';

const client = new Client({ name: 'spaceport-subscription-flow', version: '1.0.0' }, { capabilities: {} });
const transport = new SSEClientTransport(new URL(SERVER_URL));

const steps = [];
const record = (step, status, info = '') => {
  steps.push({ step, status, info });
  const tag = status === 'pass' ? '✅' : status === 'warn' ? '⚠️' : '❌';
  const suffix = info ? ` — ${info}` : '';
  console.log(`${tag} ${step}${suffix}`);
};

const extractText = (result) => result?.content?.find((c) => c.type === 'text')?.text ?? '';
const extractSnapshot = (result) => {
  const text = extractText(result);
  const match = text.match(/Page Snapshot:\n```yaml\n([\s\S]*?)```/);
  return match ? match[1] : '';
};

const findPlanRef = (snapshot, label) => {
  const marker = `link "${label}" [ref=`;
  const index = snapshot.indexOf(marker);
  if (index === -1) {
    throw new Error(`Unable to find CTA with label '${label}'. Snapshot: ${snapshot.slice(0, 400)}...`);
  }
  const start = index + marker.length;
  const end = snapshot.indexOf(']', start);
  return snapshot.slice(start, end);
};

const sessionKey = 'selectedPlan';

(async () => {
  try {
    await client.connect(transport);
    record('Connect to MCP server', 'pass', SERVER_URL);

    const navigate = await client.callTool({
      name: 'browser_navigate',
      arguments: { url: `${PREVIEW_URL.replace(/\/$/, '')}/pricing` }
    });
    record('Navigate to pricing', 'pass', PREVIEW_URL);

    const snapshot = extractSnapshot(navigate);
    const ctaLabel = PLAN_LABELS[PLAN];
    if (!ctaLabel) {
      throw new Error(`Unsupported plan '${PLAN}'. Supported: ${Object.keys(PLAN_LABELS).join(', ')}`);
    }

    const ref = findPlanRef(snapshot, ctaLabel);
    await client.callTool({
      name: 'browser_click',
      arguments: { element: ctaLabel, ref }
    });
    record('Click plan CTA', 'pass', `${PLAN} (ref=${ref})`);

    const wait = await client.callTool({
      name: 'browser_wait_for',
      arguments: { text: SUCCESS_TEXT, time: 10 }
    });
    const waitText = extractText(wait);
    record('Wait for auth page', 'pass', SUCCESS_TEXT);

    const session = await client.callTool({
      name: 'browser_evaluate',
      arguments: { function: '() => window.sessionStorage.getItem("selectedPlan")' }
    });
    const sessionRaw = extractText(session).split('\n')[1]?.trim() ?? '';
    let parsedSession = null;
    try {
      parsedSession = JSON.parse(JSON.parse(sessionRaw));
    } catch {
      try {
        parsedSession = JSON.parse(sessionRaw.replace(/^"|"$/g, ''));
      } catch {}
    }

    if (parsedSession && parsedSession.plan === PLAN) {
      record('Verify sessionStorage', 'pass', `${sessionKey}=${JSON.stringify(parsedSession)}`);
    } else {
      record('Verify sessionStorage', 'warn', `Unexpected payload: ${sessionRaw}`);
    }

    const location = await client.callTool({
      name: 'browser_evaluate',
      arguments: { function: '() => window.location.href' }
    });
    const locationRaw = extractText(location).split('\n')[1]?.trim().replace(/^"|"$/g, '');
    const expectedQuery = `plan=${PLAN}`;
    if (locationRaw?.includes('/auth') && locationRaw.includes(expectedQuery)) {
      record('Verify redirect URL', 'pass', locationRaw);
    } else {
      record('Verify redirect URL', 'fail', locationRaw ?? 'unknown');
    }
  } catch (error) {
    record('Subscription checkout flow', 'fail', error.message);
    process.exitCode = 1;
  } finally {
    await client.close().catch(() => {});
    console.log('\nSummary:', JSON.stringify(steps, null, 2));
  }
})();
