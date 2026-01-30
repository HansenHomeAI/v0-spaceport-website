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

  await callTool('browser_run_code', {
    code: `async (page) => {
      const email = ${JSON.stringify(LITCHI_EMAIL)};
      const password = ${JSON.stringify(LITCHI_PASSWORD)};
      const loginSelectors = {
        email: 'input[type="email"], input[name*="email" i], input[id*="email" i], input[type="text"]',
        password: 'input[type="password"]',
        submit: 'button[type="submit"], button:has-text("Log in"), button:has-text("Login"), button:has-text("Sign in")'
      };
      await page.goto('https://flylitchi.com/hub#/login', { waitUntil: 'domcontentloaded' });
      const pickFrame = () => page.frames().find((frame) => frame.url().includes('flylitchi.com/hub')) ?? page;
      const frame = pickFrame();
      await frame.waitForSelector(loginSelectors.email, { timeout: 20000 });
      await frame.fill(loginSelectors.email, email);
      await frame.fill(loginSelectors.password, password);
      const submit = await frame.$(loginSelectors.submit);
      if (submit) {
        await submit.click();
      }
      await page.waitForTimeout(2000);
      await page.goto('https://flylitchi.com/hub/#/missions', { waitUntil: 'domcontentloaded' });
      await page.waitForTimeout(2000);
      return { url: page.url() };
    }`
  });

  await callTool('browser_wait_for', { time: 5 }).catch(() => {});
  const snapshot = snapshotFrom(await callTool('browser_snapshot', {}));

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
