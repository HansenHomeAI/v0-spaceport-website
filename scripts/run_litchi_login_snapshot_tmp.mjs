#!/usr/bin/env node
import { Client } from '@modelcontextprotocol/sdk/client';
import { SSEClientTransport } from '@modelcontextprotocol/sdk/client/sse.js';
import { writeFileSync } from 'node:fs';

const SERVER_URL = process.env.PLAYWRIGHT_MCP_SSE_URL ?? 'http://localhost:5174/sse';
const PREVIEW_URL = process.env.PREVIEW_URL;
if (!PREVIEW_URL) {
  console.error('Missing PREVIEW_URL');
  process.exit(1);
}

const client = new Client({ name: 'spaceport-login-snapshot', version: '1.0.0' }, { capabilities: {} });
const transport = new SSEClientTransport(new URL(SERVER_URL));

function textFromResult(result) {
  return result?.content?.find((c) => c.type === 'text')?.text ?? '';
}

function snapshotFrom(result) {
  const match = textFromResult(result).match(/Page Snapshot:\n```yaml\n([\s\S]*?)```/);
  return match ? match[1] : '';
}

async function callTool(name, args) {
  return client.callTool({ name, arguments: args });
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

(async () => {
  await client.connect(transport);
  const nav = await callTool('browser_navigate', { url: `${PREVIEW_URL.replace(/\/$/, '')}/create` });
  let snapshot = snapshotFrom(nav);
  const loginRef = tryFindRef(snapshot, 'button', ['Login', 'Log in', 'Log In']);
  if (loginRef) {
    await callTool('browser_click', { element: 'Login', ref: loginRef });
    await callTool('browser_wait_for', { text: 'Email', time: 15 });
    snapshot = snapshotFrom(await callTool('browser_snapshot', {}));
  }
  writeFileSync('logs/litchi-login-snapshot.yaml', snapshot, 'utf-8');
  await client.close();
})();
