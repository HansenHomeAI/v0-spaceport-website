#!/usr/bin/env node
import { Client } from '@modelcontextprotocol/sdk/client';
import { SSEClientTransport } from '@modelcontextprotocol/sdk/client/sse.js';
import { writeFileSync } from 'node:fs';

const SERVER_URL = process.env.PLAYWRIGHT_MCP_SSE_URL ?? 'http://localhost:5174/sse';
const LITCHI_EMAIL = process.env.LITCHI_EMAIL;
const LITCHI_PASSWORD = process.env.LITCHI_PASSWORD;
const EXPECTED_MISSIONS = (process.env.LITCHI_EXPECTED_MISSIONS ?? 'Untitled - 1,Untitled - 2')
  .split(',')
  .map((value) => value.trim())
  .filter(Boolean);

if (!LITCHI_EMAIL || !LITCHI_PASSWORD) {
  console.error('Missing required env vars: LITCHI_EMAIL, LITCHI_PASSWORD');
  process.exit(1);
}

const client = new Client({ name: 'spaceport-litchi-hub-check', version: '1.0.0' }, { capabilities: {} });
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

function hasText(snapshot, text) {
  return new RegExp(escapeRegex(text), 'i').test(snapshot);
}

(async () => {
  await client.connect(transport);

  const nav = await callTool('browser_navigate', { url: 'https://flylitchi.com/hub/#/login' });
  let snapshot = snapshotFrom(nav);

  const frameInfo = await callTool('browser_evaluate', {
    function: `() => ({
      url: window.location.href,
      frames: Array.from(document.querySelectorAll('iframe')).map((frame) => frame.src || '')
    })`
  });
  console.log(textFromResult(frameInfo));

  const loginRef = tryFindRef(snapshot, 'link', ['Login', 'Log In', 'Sign in'])
    ?? tryFindRef(snapshot, 'button', ['Login', 'Log In', 'Sign in', 'login Log In']);
  if (loginRef) {
    await callTool('browser_click', { element: 'Login', ref: loginRef });
    const tabsAfterLogin = await callTool('browser_tabs', { action: 'list' });
    console.log(textFromResult(tabsAfterLogin));
    await callTool('browser_wait_for', { text: 'Email', time: 20 }).catch(() => {});
    snapshot = snapshotFrom(await callTool('browser_snapshot', {}));
  } else {
    await callTool('browser_evaluate', {
      function: `() => {
        const candidates = Array.from(document.querySelectorAll('button,a'));
        const target = candidates.find((el) => /log\\s*in/i.test(el.textContent || ''));
        if (!target) return false;
        target.click();
        return true;
      }`
    });
    const tabsAfterEval = await callTool('browser_tabs', { action: 'list' });
    console.log(textFromResult(tabsAfterEval));
    await callTool('browser_wait_for', { text: 'Email', time: 20 }).catch(() => {});
    snapshot = snapshotFrom(await callTool('browser_snapshot', {}));
  }

  const emailRef = tryFindRef(snapshot, 'textbox', ['Email', 'E-mail']);
  const passwordRef = tryFindRef(snapshot, 'textbox', ['Password']);
  const signInRef = tryFindRef(snapshot, 'button', ['Log In', 'Login', 'Sign in', 'Sign In']);

  if (emailRef && passwordRef && signInRef) {
    await callTool('browser_fill_form', {
      fields: [
        { name: 'Email', type: 'textbox', ref: emailRef, value: LITCHI_EMAIL },
        { name: 'Password', type: 'textbox', ref: passwordRef, value: LITCHI_PASSWORD }
      ]
    });
    await callTool('browser_click', { element: 'Log In', ref: signInRef });
  }

  if (!emailRef || !passwordRef || !signInRef) {
    await callTool('browser_navigate', { url: 'https://flylitchi.com/hub' });
    await callTool('browser_wait_for', { text: 'Log In', time: 20 }).catch(() => {});
  }

  await callTool('browser_navigate', { url: 'https://flylitchi.com/hub/#/missions' });
  await callTool('browser_wait_for', { text: 'MISSIONS', time: 30 }).catch(() => {});
  snapshot = snapshotFrom(await callTool('browser_snapshot', {}));

  const missionsRef = tryFindRef(snapshot, 'button', ['MISSIONS', 'Missions']);
  if (missionsRef) {
    await callTool('browser_click', { element: 'MISSIONS', ref: missionsRef });
    await callTool('browser_wait_for', { text: 'Missions', time: 20 }).catch(() => {});
    snapshot = snapshotFrom(await callTool('browser_snapshot', {}));
  }

  await callTool('browser_take_screenshot', {
    filename: '/Users/gabrielhansen/Spaceport-Website copy/logs/litchi-hub-missions.png',
    fullPage: true
  });

  const results = EXPECTED_MISSIONS.map((mission) => ({
    mission,
    found: hasText(snapshot, mission)
  }));

  writeFileSync('logs/litchi-hub-snapshot.yaml', snapshot, 'utf-8');
  console.log(JSON.stringify({ results }, null, 2));

  await client.close();
})();
