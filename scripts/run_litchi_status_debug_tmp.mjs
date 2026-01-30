#!/usr/bin/env node
import { Client } from '@modelcontextprotocol/sdk/client';
import { SSEClientTransport } from '@modelcontextprotocol/sdk/client/sse.js';
import { writeFileSync } from 'node:fs';

const SERVER_URL = process.env.PLAYWRIGHT_MCP_SSE_URL ?? 'http://localhost:5174/sse';
const PREVIEW_URL = process.env.PREVIEW_URL;
const SPACEPORT_EMAIL = process.env.SPACEPORT_EMAIL;
const SPACEPORT_PASSWORD = process.env.SPACEPORT_PASSWORD;
const STATUS_URL = process.env.LITCHI_STATUS_URL;

if (!PREVIEW_URL || !SPACEPORT_EMAIL || !SPACEPORT_PASSWORD || !STATUS_URL) {
  console.error('Missing env vars PREVIEW_URL, SPACEPORT_EMAIL, SPACEPORT_PASSWORD, LITCHI_STATUS_URL');
  process.exit(1);
}

const client = new Client({ name: 'spaceport-litchi-status-debug', version: '1.0.0' }, { capabilities: {} });
const transport = new SSEClientTransport(new URL(SERVER_URL));

function textFromResult(result) {
  return result?.content?.find((c) => c.type === 'text')?.text ?? '';
}

function jsonFromToolResult(result) {
  const text = textFromResult(result);
  const match = text.match(/### Result\s*\n([\s\S]*?)(?:\n###|\n$)/);
  const payload = match ? match[1].trim() : text.trim();
  return JSON.parse(payload);
}

function snapshotFrom(result) {
  const text = textFromResult(result);
  const match = text.match(/(?:Page )?Snapshot:?\s*```yaml\s*([\s\S]*?)```/);
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

(async () => {
  await client.connect(transport);
  const nav = await callTool('browser_navigate', { url: `${PREVIEW_URL.replace(/\/$/, '')}/create` });
  let snapshot = snapshotFrom(nav);

  const signOutRef = tryFindRef(snapshot, 'button', ['Sign Out']);
  if (signOutRef) {
    await callTool('browser_click', { element: 'Sign Out', ref: signOutRef });
    await callTool('browser_wait_for', { text: 'Login', time: 20 }).catch(() => {});
    snapshot = snapshotFrom(await callTool('browser_snapshot', {}));
  }

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
    await callTool('browser_wait_for', { text: 'Litchi Mission Control', time: 30 });
  }

  const tokenResult = await callTool('browser_evaluate', {
    function: `async () => {
      const keys = Object.keys(localStorage);
      const tokenKey = keys.find((key) => key.endsWith('.idToken'));
      if (!tokenKey) return { ok: false, error: 'missing_token', keys };
      return { ok: true, token: localStorage.getItem(tokenKey) };
    }`
  });

  const tokenPayload = jsonFromToolResult(tokenResult);
  if (!tokenPayload.ok || !tokenPayload.token) {
    console.error('Missing auth token', tokenPayload);
    await client.close();
    process.exit(1);
  }

  const response = await fetch(STATUS_URL, {
    headers: { Authorization: `Bearer ${tokenPayload.token}` }
  });
  const text = await response.text();
  const resultPayload = {
    ok: response.ok,
    status: response.status,
    requestId: response.headers.get('x-amzn-requestid'),
    text
  };
  const resultText = JSON.stringify(resultPayload, null, 2);
  writeFileSync('logs/litchi-status-full.json', resultText, 'utf-8');
  console.log(resultText.slice(0, 500));
  await client.close();
})();
