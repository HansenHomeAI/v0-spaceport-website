#!/usr/bin/env node
import { Client } from '@modelcontextprotocol/sdk/client';
import { SSEClientTransport } from '@modelcontextprotocol/sdk/client/sse.js';

const SERVER_URL = process.env.PLAYWRIGHT_MCP_SSE_URL ?? 'http://localhost:5174/sse';
const LITCHI_EMAIL = process.env.LITCHI_EMAIL;
const LITCHI_PASSWORD = process.env.LITCHI_PASSWORD;
const EXPECTED_NAMES = (process.env.LITCHI_EXPECTED_NAMES ?? '')
  .split(',')
  .map((value) => value.trim())
  .filter(Boolean);

if (!LITCHI_EMAIL || !LITCHI_PASSWORD) {
  console.error('Missing env vars LITCHI_EMAIL, LITCHI_PASSWORD');
  process.exit(1);
}

const client = new Client({ name: 'spaceport-litchi-hub-verify', version: '1.0.0' }, { capabilities: {} });
const transport = new SSEClientTransport(new URL(SERVER_URL));

function textFromResult(result) {
  return result?.content?.find((c) => c.type === 'text')?.text ?? '';
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

async function callTool(name, args, { silent } = {}) {
  const result = await client.callTool({ name, arguments: args });
  if (!silent) {
    const text = textFromResult(result);
    if (text) console.log(text);
  }
  return result;
}

(async () => {
  await client.connect(transport);
  await callTool('browser_navigate', { url: 'https://flylitchi.com/hub' }, { silent: true });
  let snapshot = snapshotFrom(await callTool('browser_snapshot', {}, { silent: true }));

  const loginLinkRef = tryFindRef(snapshot, 'link', ['Log In', 'Login']);
  if (loginLinkRef) {
    await callTool('browser_click', { element: 'Log In', ref: loginLinkRef }, { silent: true });
    await callTool('browser_wait_for', { text: 'Email', time: 20 }, { silent: true });
    snapshot = snapshotFrom(await callTool('browser_snapshot', {}, { silent: true }));
  }

  const emailRef = tryFindRef(snapshot, 'textbox', ['Email']);
  const passwordRef = tryFindRef(snapshot, 'textbox', ['Password']);
  const submitRef = tryFindRef(snapshot, 'button', ['Log In', 'Login', 'Sign In']);

  if (emailRef && passwordRef && submitRef) {
    await callTool('browser_fill_form', {
      fields: [
        { name: 'Email', type: 'textbox', ref: emailRef, value: LITCHI_EMAIL },
        { name: 'Password', type: 'textbox', ref: passwordRef, value: LITCHI_PASSWORD }
      ]
    }, { silent: true });
    await callTool('browser_click', { element: 'Log In', ref: submitRef }, { silent: true });
  }

  await callTool('browser_wait_for', { text: 'Missions', time: 30 }, { silent: true });
  const hubSnapshot = await callTool('browser_snapshot', {}, { silent: true });
  const hubSnapshotText = snapshotFrom(hubSnapshot);
  if (hubSnapshotText) {
    const { writeFileSync } = await import('node:fs');
    writeFileSync('logs/litchi-hub-snapshot.yaml', hubSnapshotText, 'utf-8');
  }

  const missionsRef = tryFindRef(hubSnapshotText, 'link', ['Missions', 'Mission']);
  if (missionsRef) {
    await callTool('browser_click', { element: 'Missions', ref: missionsRef }, { silent: true });
  }
  await callTool('browser_wait_for', { time: 5 }, { silent: true });

  const pageTextResult = await callTool('browser_evaluate', {
    function: '() => document.body.innerText'
  }, { silent: true });
  const pageText = textFromResult(pageTextResult);

  const results = EXPECTED_NAMES.map((name) => ({ name, found: pageText.includes(name) }));
  const ok = results.every((item) => item.found);
  console.log(JSON.stringify({ ok, results }, null, 2));
  await client.close();
  process.exit(ok ? 0 : 1);
})().catch(async (err) => {
  console.error(err);
  try {
    await client.close();
  } catch {}
  process.exit(1);
});
