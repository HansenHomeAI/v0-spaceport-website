#!/usr/bin/env node
import { Client } from '@modelcontextprotocol/sdk/client';
import { SSEClientTransport } from '@modelcontextprotocol/sdk/client/sse.js';

const SERVER_URL = process.env.PLAYWRIGHT_MCP_SSE_URL ?? 'http://localhost:5174/sse';
const TARGET_URL = process.argv[2] ?? 'https://spcprt.com';

const client = new Client(
  { name: 'spaceport-feedback-flow', version: '1.0.0' },
  { capabilities: {} }
);
const transport = new SSEClientTransport(new URL(SERVER_URL));

const steps = [];

function logStep(step, status, info = '') {
  steps.push({ step, status, info });
  const tag = status === 'pass' ? '✅' : status === 'warn' ? '⚠️' : '❌';
  const suffix = info ? ` — ${info}` : '';
  console.log(`${tag} ${step}${suffix}`);
}

function extractSnapshot(result) {
  const textItem = result?.content?.find((entry) => entry.type === 'text');
  if (!textItem) return '';
  const match = textItem.text.match(/Page Snapshot:\n```yaml\n([\s\S]*?)```/);
  return match ? match[1] : '';
}

function escapeRegex(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function findRef(snapshot, role, label) {
  const regex = new RegExp(`- ${role} \\\"${escapeRegex(label)}\\\"(?: \\[[^\\]]+\\])* \\[ref=(e\\d+)`, 'i');
  const match = snapshot.match(regex);
  if (!match) throw new Error(`Unable to locate ref for ${role} ${label}`);
  return match[1];
}

async function callTool(name, args) {
  return client.callTool({ name, arguments: args });
}

function uniqueMessage() {
  const stamp = new Date().toISOString().replace(/[-:T.Z]/g, '').slice(0, 14);
  return `MCP feedback run ${stamp}`;
}

async function main() {
  try {
    await client.connect(transport);
    logStep('Connect to MCP server', 'pass', `via ${SERVER_URL}`);

    const navigate = await callTool('browser_navigate', { url: TARGET_URL });
    const snapshot = extractSnapshot(navigate);
    logStep('Navigate to site', 'pass', TARGET_URL);

    const feedbackRef = findRef(snapshot, 'textbox', 'How can we improve?');
    const submitRef = findRef(snapshot, 'button', 'Send Feedback');

    const message = uniqueMessage();
    await callTool('browser_fill_form', {
      fields: [
        { name: 'How can we improve?', type: 'textbox', ref: feedbackRef, value: message }
      ]
    });
    logStep('Populate feedback input', 'pass', message);

    await callTool('browser_click', { element: 'Send Feedback', ref: submitRef });
    logStep('Submit feedback form', 'pass');

    const waitResponse = await callTool('browser_wait_for', {
      text: 'Thanks for sharing your feedback!',
      time: 2
    });
    const waitSnapshot = extractSnapshot(waitResponse);
    const confirmationVisible = /Thanks for sharing your feedback!/.test(waitSnapshot);
    logStep('Confirm success message', confirmationVisible ? 'pass' : 'warn');
    if (!confirmationVisible && waitSnapshot) {
      console.warn('Snapshot excerpt:', waitSnapshot.slice(0, 200));
    }

    const finalSnapshot = extractSnapshot(await callTool('browser_snapshot', {}));
    const messagePersisted = finalSnapshot.includes(message);
    logStep('Verify message cleared', messagePersisted ? 'warn' : 'pass');
  } catch (error) {
    logStep('Feedback flow failed', 'fail', error.message ?? String(error));
    process.exitCode = 1;
  } finally {
    await client.close().catch(() => undefined);
  }
}

await main();
