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

const client = new Client({ name: 'spaceport-litchi-connect', version: '1.0.0' }, { capabilities: {} });
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
    snapshot = snapshotFrom(await callTool('browser_snapshot', {}));
  }

  const connectButtonRef = tryFindRef(snapshot, 'button', ['Connect Litchi Account', 'Enter 2FA Code']);
  if (connectButtonRef) {
    await callTool('browser_click', { element: 'Connect Litchi Account', ref: connectButtonRef });
  }

  await callTool('browser_wait_for', { text: 'Connect Litchi Account', time: 10 });
  snapshot = snapshotFrom(await callTool('browser_snapshot', {}));

  const litchiEmailRef = tryFindRef(snapshot, 'textbox', ['Email']);
  const litchiPasswordRef = tryFindRef(snapshot, 'textbox', ['Password']);
  if (litchiEmailRef && litchiPasswordRef) {
    await callTool('browser_fill_form', {
      fields: [
        { name: 'Email', type: 'textbox', ref: litchiEmailRef, value: LITCHI_EMAIL },
        { name: 'Password', type: 'textbox', ref: litchiPasswordRef, value: LITCHI_PASSWORD }
      ]
    });
  }

  const submitRef = tryFindRef(snapshot, 'button', ['Connect']);
  if (submitRef) {
    await callTool('browser_click', { element: 'Connect', ref: submitRef });
  }

  await callTool('browser_wait_for', { text: 'Litchi session connected', time: 60 }).catch(() => {});
  const finalSnapshot = snapshotFrom(await callTool('browser_snapshot', {}));
  writeFileSync('logs/litchi-connect-after.yaml', finalSnapshot, 'utf-8');

  const connected = /Litchi session connected|Connected/i.test(finalSnapshot);
  const loginFailed = /Login failed/i.test(finalSnapshot);
  console.log(`connected_text=${connected}`);
  console.log(`login_failed=${loginFailed}`);

  await client.close();
})();
