#!/usr/bin/env node
import fs from 'node:fs';
import { Client } from '@modelcontextprotocol/sdk/client';
import { SSEClientTransport } from '@modelcontextprotocol/sdk/client/sse.js';

const SERVER_URL = process.env.PLAYWRIGHT_MCP_SSE_URL ?? 'http://localhost:5174/sse';
const PREVIEW_URL = process.env.PREVIEW_URL ?? process.argv[2];
const EMAIL = process.env.TEST_EMAIL;
const PASSWORD = process.env.TEST_PASSWORD;

if (!PREVIEW_URL) {
  console.error('PREVIEW_URL must be set (or passed as an argument).');
  process.exit(1);
}

if (!EMAIL || !PASSWORD) {
  console.error('TEST_EMAIL and TEST_PASSWORD must be set.');
  process.exit(1);
}

const client = new Client(
  { name: 'spaceport-login-validation', version: '1.0.0' },
  { capabilities: {} }
);
const transport = new SSEClientTransport(new URL(SERVER_URL));

const steps = [];
const runStamp = new Date().toISOString().replace(/[-:T.Z]/g, '').slice(0, 14);

function record(step, status, info = '') {
  steps.push({ step, status, info });
  const tag = status === 'pass' ? '✅' : status === 'warn' ? '⚠️' : '❌';
  const suffix = info ? ` — ${info}` : '';
  console.log(`${tag} ${step}${suffix}`);
}

function extractText(result) {
  return result?.content?.find((entry) => entry.type === 'text')?.text ?? '';
}

function extractSnapshot(result) {
  const match = extractText(result).match(/Page Snapshot:\n```yaml\n([\s\S]*?)```/);
  return match ? match[1] : '';
}

function escapeRegex(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function findRef(snapshot, role, label) {
  const regex = new RegExp(
    `- ${role} \\\"${escapeRegex(label)}\\\"(?: \\[[^\\]]+\\])* \\[ref=(e\\d+)`,
    'i'
  );
  const match = snapshot.match(regex);
  if (!match) {
    throw new Error(`Unable to locate ref for ${role} ${label}`);
  }
  return match[1];
}

function findOptionalRef(snapshot, role, label) {
  const regex = new RegExp(
    `- ${role} \\\"${escapeRegex(label)}\\\"(?: \\[[^\\]]+\\])* \\[ref=(e\\d+)`,
    'i'
  );
  const match = snapshot.match(regex);
  return match ? match[1] : null;
}

function findFirstRef(snapshot, role, labels) {
  for (const label of labels) {
    const ref = findOptionalRef(snapshot, role, label);
    if (ref) return ref;
  }
  return null;
}

function buildAuthUrl(baseUrl) {
  const url = new URL(baseUrl);
  if (!url.pathname.endsWith('/auth')) {
    url.pathname = url.pathname.replace(/\/$/, '') + '/auth';
  }
  url.searchParams.set('checkout', '1');
  return url.toString();
}

async function callTool(name, args, { expectSnapshot = false } = {}) {
  const result = await client.callTool({ name, arguments: args });
  if (expectSnapshot && !extractSnapshot(result)) {
    throw new Error(`${name} did not return a snapshot`);
  }
  return result;
}

async function main() {
  try {
    await client.connect(transport);
    record('Connect to MCP server', 'pass', `via ${SERVER_URL}`);

    const authUrl = buildAuthUrl(PREVIEW_URL);
    const navigate = await callTool('browser_navigate', { url: authUrl }, { expectSnapshot: true });
    let snapshot = extractSnapshot(navigate);
    record('Navigate to auth page', 'pass', authUrl);

    if (/Signed in successfully/i.test(snapshot) || /New Project/i.test(snapshot) || /Dashboard/i.test(snapshot)) {
      record('Already authenticated', 'pass');
      return;
    }

    let emailRef = findFirstRef(snapshot, 'textbox', ['Email', 'Email Address', 'Email address']);
    let passwordRef = findFirstRef(snapshot, 'textbox', ['Password']);

    if (!passwordRef) {
      const loginToggleRef = findFirstRef(snapshot, 'button', ['Login', 'Sign in', 'Sign In']);
      if (!loginToggleRef) {
        const debugPath = `logs/login-validation-snapshot-${runStamp}.yaml`;
        try {
          fs.writeFileSync(debugPath, snapshot);
          record('Save debug snapshot', 'warn', debugPath);
        } catch (writeError) {
          record('Save debug snapshot', 'warn', 'failed to write snapshot');
        }
        throw new Error('Unable to locate login toggle button');
      }

      await callTool('browser_click', { element: 'Login', ref: loginToggleRef });
      record('Switch to login mode', 'pass');

      await callTool('browser_wait_for', { text: 'Password', time: 4 });
      const loginSnapshot = extractSnapshot(await callTool('browser_snapshot', {}));
      snapshot = loginSnapshot || snapshot;

      emailRef = findFirstRef(snapshot, 'textbox', ['Email', 'Email Address', 'Email address']);
      passwordRef = findFirstRef(snapshot, 'textbox', ['Password']);
    }

    if (!emailRef || !passwordRef) {
      const debugPath = `logs/login-validation-snapshot-${runStamp}.yaml`;
      try {
        fs.writeFileSync(debugPath, snapshot);
        record('Save debug snapshot', 'warn', debugPath);
      } catch (writeError) {
        record('Save debug snapshot', 'warn', 'failed to write snapshot');
      }
      throw new Error('Unable to locate login email/password fields');
    }

    await callTool('browser_fill_form', {
      fields: [
        { name: 'Email', type: 'textbox', ref: emailRef, value: EMAIL },
        { name: 'Password', type: 'textbox', ref: passwordRef, value: PASSWORD }
      ]
    });
    record('Fill login form', 'pass', EMAIL);

    const signInRef = findRef(snapshot, 'button', 'Sign in');
    await callTool('browser_click', { element: 'Sign in', ref: signInRef });
    record('Submit login form', 'pass');

    await callTool('browser_wait_for', { text: 'Signed in successfully', time: 8 });
    const signedInSnapshot = extractSnapshot(await callTool('browser_snapshot', {}));
    const signedIn = /Signed in successfully/i.test(signedInSnapshot);

    if (signedIn) {
      record('Confirm sign-in success', 'pass');
      return;
    }

    await callTool('browser_wait_for', { text: 'New Project', time: 8 });
    const createSnapshot = extractSnapshot(await callTool('browser_snapshot', {}));
    const createVisible = /New Project/i.test(createSnapshot);

    record('Confirm login redirect', createVisible ? 'pass' : 'warn');

    if (!createVisible) {
      record('Login validation failed', 'fail', 'Success signal not detected');
      process.exitCode = 1;
    }
  } catch (error) {
    record('Login validation failed', 'fail', error.message ?? String(error));
    process.exitCode = 1;
  } finally {
    await client.close().catch(() => undefined);
  }
}

await main();
