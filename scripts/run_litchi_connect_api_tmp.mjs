#!/usr/bin/env node
import { Client } from '@modelcontextprotocol/sdk/client';
import { SSEClientTransport } from '@modelcontextprotocol/sdk/client/sse.js';

const SERVER_URL = process.env.PLAYWRIGHT_MCP_SSE_URL ?? 'http://localhost:5174/sse';
const PREVIEW_URL = process.env.PREVIEW_URL;
const SPACEPORT_EMAIL = process.env.SPACEPORT_EMAIL;
const SPACEPORT_PASSWORD = process.env.SPACEPORT_PASSWORD;
const CONNECT_URL = process.env.LITCHI_CONNECT_URL;
const LITCHI_EMAIL = process.env.LITCHI_EMAIL;
const LITCHI_PASSWORD = process.env.LITCHI_PASSWORD;

if (!PREVIEW_URL || !SPACEPORT_EMAIL || !SPACEPORT_PASSWORD || !CONNECT_URL || !LITCHI_EMAIL || !LITCHI_PASSWORD) {
  console.error('Missing env vars PREVIEW_URL, SPACEPORT_EMAIL, SPACEPORT_PASSWORD, LITCHI_CONNECT_URL, LITCHI_EMAIL, LITCHI_PASSWORD');
  process.exit(1);
}

const client = new Client({ name: 'spaceport-litchi-connect-api', version: '1.0.0' }, { capabilities: {} });
const transport = new SSEClientTransport(new URL(SERVER_URL));

function textFromResult(result) {
  return result?.content?.find((c) => c.type === 'text')?.text ?? '';
}

function snapshotFrom(result) {
  const match = textFromResult(result).match(/Page Snapshot:\n```yaml\n([\s\S]*?)```/);
  return match ? match[1] : '';
}

function escapeRegex(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function tryFindRef(snapshot, role, labels) {
  for (const label of labels) {
    const regex = new RegExp(`- ${role} \\"${escapeRegex(label)}\\"(?: \\[[^\\]]+\\])* \\[ref=(e\\d+)`, 'i');
    const match = snapshot.match(regex);
    if (match) return match[1];
  }
  return null;
}

async function callTool(name, args) {
  return client.callTool({ name, arguments: args });
}

(async () => {
  await client.connect(transport);
  const nav = await callTool('browser_navigate', { url: `${PREVIEW_URL.replace(/\/$/, '')}/create` });
  let snapshot = snapshotFrom(nav);

  const loginButtonRef = tryFindRef(snapshot, 'button', ['Login', 'Log in', 'Log In']);
  if (loginButtonRef) {
    await callTool('browser_click', { element: 'Login', ref: loginButtonRef });
    await callTool('browser_wait_for', { text: 'Email', time: 15 }).catch(() => {});
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
    await callTool('browser_wait_for', { text: 'Litchi Mission Control', time: 30 }).catch(() => {});
  }

  const result = await callTool('browser_evaluate', {
    function: `async () => {
      const keys = Object.keys(localStorage);
      const tokenKey = keys.find((key) => key.endsWith('.idToken'));
      if (!tokenKey) return { ok: false, error: 'missing_token', keys };
      const token = localStorage.getItem(tokenKey);
      const response = await fetch(${JSON.stringify(CONNECT_URL)}, {
        method: 'POST',
        headers: { Authorization: 'Bearer ' + token, 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: ${JSON.stringify(LITCHI_EMAIL)}, password: ${JSON.stringify(LITCHI_PASSWORD)} })
      });
      const text = await response.text();
      return { ok: response.ok, status: response.status, text: text.slice(0, 500) };
    }`
  });

  console.log(textFromResult(result));
  await client.close();
})();
