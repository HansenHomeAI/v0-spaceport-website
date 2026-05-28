#!/usr/bin/env node
import { Client } from '@modelcontextprotocol/sdk/client';
import { SSEClientTransport } from '@modelcontextprotocol/sdk/client/sse.js';
import { writeFileSync } from 'node:fs';

const SERVER_URL = process.env.PLAYWRIGHT_MCP_SSE_URL ?? 'http://localhost:5174/sse';
const PREVIEW_URL = process.env.PREVIEW_URL;
const SPACEPORT_EMAIL = process.env.SPACEPORT_EMAIL;
const SPACEPORT_PASSWORD = process.env.SPACEPORT_PASSWORD;
const LITCHI_EMAIL = process.env.LITCHI_EMAIL ?? SPACEPORT_EMAIL;
const LITCHI_PASSWORD = process.env.LITCHI_PASSWORD;

if (!PREVIEW_URL || !SPACEPORT_EMAIL || !SPACEPORT_PASSWORD || !LITCHI_EMAIL || !LITCHI_PASSWORD) {
  console.error('Missing required env vars: PREVIEW_URL, SPACEPORT_EMAIL, SPACEPORT_PASSWORD, LITCHI_EMAIL, LITCHI_PASSWORD');
  process.exit(1);
}

const client = new Client({ name: 'spaceport-litchi-debug', version: '1.0.0' }, { capabilities: {} });
const transport = new SSEClientTransport(new URL(SERVER_URL));

function textFromResult(result) {
  return result?.content?.find((c) => c.type === 'text')?.text ?? '';
}

function snapshotFrom(result) {
  const text = textFromResult(result);
  const match = text.match(/Page Snapshot:\n```yaml\n([\s\S]*?)```/);
  return match ? match[1] : '';
}

function escapeRegex(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function tryFindRef(snapshot, role, labels) {
  for (const label of labels) {
    const regex = new RegExp(`- ${role} \\\"${escapeRegex(label)}\\\"(?: \\[[^\\]]+\\])* \\[ref=(e\\d+)`, 'i');
    const match = snapshot.match(regex);
    if (match) return match[1];
  }
  return null;
}

async function callTool(name, args) {
  return client.callTool({ name, arguments: args });
}

async function waitForText(text, time = 20) {
  const result = await callTool('browser_wait_for', { text, time });
  return snapshotFrom(result);
}

(async () => {
  await client.connect(transport);
  const nav = await callTool('browser_navigate', { url: `${PREVIEW_URL.replace(/\/$/, '')}/create` });
  let snapshot = snapshotFrom(nav);

  const loginButtonRef = tryFindRef(snapshot, 'button', ['Login', 'Log in', 'Log In']);
  if (loginButtonRef) {
    await callTool('browser_click', { element: 'Login', ref: loginButtonRef });
    await callTool('browser_wait_for', { text: 'Email', time: 15 });
    snapshot = snapshotFrom(await callTool('browser_snapshot', {}));
  }

  const emailRef = tryFindRef(snapshot, 'textbox', ['Email']);
  const passwordRef = tryFindRef(snapshot, 'textbox', ['Password']);
  const signInRef = tryFindRef(snapshot, 'button', ['Sign in', 'Sign In']);

  if (emailRef && passwordRef && signInRef) {
    await callTool('browser_fill_form', {
      fields: [
        { name: 'Email', type: 'textbox', ref: emailRef, value: SPACEPORT_EMAIL },
        { name: 'Password', type: 'textbox', ref: passwordRef, value: SPACEPORT_PASSWORD }
      ]
    });
    await callTool('browser_click', { element: 'Sign in', ref: signInRef });
    await callTool('browser_wait_for', { text: 'New Project', time: 30 });
    snapshot = snapshotFrom(await callTool('browser_snapshot', {}));
  }

  await callTool('browser_evaluate', {
    function: '() => { const el = document.querySelector(".new-project-card"); if (!el) return false; el.click(); return true; }'
  });

  await waitForText('Delivery & Automation', 20);
  snapshot = snapshotFrom(await callTool('browser_snapshot', {}));

  let sendRef = tryFindRef(snapshot, 'button', ['Send to Litchi']);
  const connectRef = tryFindRef(snapshot, 'button', ['Connect Litchi Account', 'Enter 2FA Code']);

  if (!sendRef && connectRef) {
    await callTool('browser_click', { element: 'Connect Litchi Account', ref: connectRef });
    await callTool('browser_evaluate', {
      function: `() => {
        const email = document.querySelector('#litchi-inline-email');
        const password = document.querySelector('#litchi-inline-password');
        if (!email || !password) return false;
        email.value = ${JSON.stringify(LITCHI_EMAIL)};
        email.dispatchEvent(new Event('input', { bubbles: true }));
        password.value = ${JSON.stringify(LITCHI_PASSWORD)};
        password.dispatchEvent(new Event('input', { bubbles: true }));
        return true;
      }`
    });
    await callTool('browser_evaluate', {
      function: '() => { const btn = document.querySelector(".litchi-form button[type=submit]"); if (!btn) return false; btn.click(); return true; }'
    });
    await waitForText('Send to Litchi', 30);
    snapshot = snapshotFrom(await callTool('browser_snapshot', {}));
    sendRef = tryFindRef(snapshot, 'button', ['Send to Litchi']);
  }

  if (sendRef) {
    await callTool('browser_evaluate', {
      function: `() => {
        const input = document.querySelector('#address-search');
        if (!input) return false;
        input.value = '38.27371, -78.1695';
        input.dispatchEvent(new Event('input', { bubbles: true }));
        input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', bubbles: true }));
        input.dispatchEvent(new KeyboardEvent('keyup', { key: 'Enter', code: 'Enter', bubbles: true }));
        return true;
      }`
    });

    await callTool('browser_evaluate', {
      function: `() => {
        const duration = document.querySelector('input[placeholder="Duration"]');
        const quantity = document.querySelector('input[placeholder="Quantity"]');
        if (!duration || !quantity) return false;
        duration.value = '10';
        duration.dispatchEvent(new Event('input', { bubbles: true }));
        quantity.value = '2';
        quantity.dispatchEvent(new Event('input', { bubbles: true }));
        return true;
      }`
    });

    await callTool('browser_click', { element: 'Send to Litchi', ref: sendRef });
    await callTool('browser_wait_for', { text: 'Uploading', time: 20 }).catch(() => {});
  }

  const afterResult = await callTool('browser_snapshot', {});
  const after = snapshotFrom(afterResult);
  if (after) {
    writeFileSync('logs/litchi-ui-after-send-2.yaml', after, 'utf-8');
  } else {
    const raw = textFromResult(afterResult);
    writeFileSync('logs/litchi-ui-after-send-2.raw.txt', raw, 'utf-8');
  }

  const hasUpload = /Litchi upload started|Uploading|Queued/i.test(after);
  const hasError = /Failed to fetch|error/i.test(after);
  console.log(`upload_text=${hasUpload}`);
  console.log(`error_text=${hasError}`);

  await client.close();
})();
