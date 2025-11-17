#!/usr/bin/env node
import { Client } from '@modelcontextprotocol/sdk/client';
import { SSEClientTransport } from '@modelcontextprotocol/sdk/client/sse.js';

const SERVER_URL = process.env.PLAYWRIGHT_MCP_SSE_URL ?? 'http://localhost:5174/sse';
const WAITLIST_URL = process.argv[2] ?? 'https://spcprt.com/create';

const client = new Client(
  { name: 'spaceport-waitlist-flow', version: '1.0.0' },
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

function findRef(snapshot, type, label) {
  const pattern = new RegExp(`- ${type} "${label}" \\[ref=(e\\d+)`, 'i');
  const match = snapshot.match(pattern);
  if (!match) {
    throw new Error(`Could not find ref for ${type} ${label}`);
  }
  return match[1];
}

async function callTool(name, args, { expectSnapshot = false } = {}) {
  const result = await client.callTool({ name, arguments: args });
  if (expectSnapshot && !extractSnapshot(result)) {
    throw new Error(`${name} did not return a snapshot`);
  }
  return result;
}

function randomEmail() {
  const stamp = new Date().toISOString().replace(/[-:T.Z]/g, '').slice(0, 14);
  return `agent+mcp-${stamp}@example.com`;
}

async function main() {
  try {
    await client.connect(transport);
    record('Connect to MCP server', 'pass', `via ${SERVER_URL}`);

    const navigate = await callTool('browser_navigate', { url: WAITLIST_URL }, { expectSnapshot: true });
    const navSnapshot = extractSnapshot(navigate);
    record('Navigate to waitlist page', 'pass', WAITLIST_URL);

    const nameRef = findRef(navSnapshot, 'textbox', 'Name');
    const emailRef = findRef(navSnapshot, 'textbox', 'Email Address');
    const submitRef = findRef(navSnapshot, 'button', 'Join Waitlist');

    const email = randomEmail();
    await callTool('browser_fill_form', {
      fields: [
        { name: 'Name', type: 'textbox', ref: nameRef, value: 'Automation Agent' },
        { name: 'Email Address', type: 'textbox', ref: emailRef, value: email }
      ]
    });
    record('Fill waitlist form', 'pass', email);

    await callTool('browser_click', { element: 'Join Waitlist', ref: submitRef });
    record('Submit waitlist form', 'pass');

    await callTool('browser_handle_dialog', { accept: true });
    record('Acknowledge confirmation dialog', 'pass');

    const wait = await callTool('browser_wait_for', { text: 'Join Waitlist', time: 2 }, { expectSnapshot: true });
    const waitSnapshot = extractSnapshot(wait);
    const buttonRestored = /button "Join Waitlist" \[ref=/.test(waitSnapshot);
    record('Wait for button reset', buttonRestored ? 'pass' : 'warn');

    const finalSnapshot = extractSnapshot(await callTool('browser_snapshot', {}));
    const stillFilled = /Automation Agent/.test(finalSnapshot) && finalSnapshot.includes(email);
    record('Capture final snapshot', 'pass', stillFilled ? 'Form retains values' : 'Form cleared');
  } catch (error) {
    record('Waitlist flow failed', 'fail', error.message);
    process.exitCode = 1;
  } finally {
    await client.close().catch(() => {});
  }
}

await main();
