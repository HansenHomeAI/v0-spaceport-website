#!/usr/bin/env node
import { Client } from '@modelcontextprotocol/sdk/client';
import { SSEClientTransport } from '@modelcontextprotocol/sdk/client/sse.js';
import { writeFileSync } from 'node:fs';

const SERVER_URL = process.env.PLAYWRIGHT_MCP_SSE_URL ?? 'http://localhost:5174/sse';
const PREVIEW_URL = process.env.PREVIEW_URL ?? 'http://localhost:3000';
const SPACEPORT_EMAIL = process.env.SPACEPORT_EMAIL;
const SPACEPORT_PASSWORD = process.env.SPACEPORT_PASSWORD;
const LITCHI_EMAIL = process.env.LITCHI_EMAIL ?? SPACEPORT_EMAIL;
const LITCHI_PASSWORD = process.env.LITCHI_PASSWORD;
const BATTERY_MINUTES = process.env.LITCHI_BATTERY_MINUTES ?? '10';
const BATTERY_COUNT = process.env.LITCHI_BATTERY_COUNT ?? '2';

if (!PREVIEW_URL || !SPACEPORT_EMAIL || !SPACEPORT_PASSWORD || !LITCHI_EMAIL || !LITCHI_PASSWORD) {
  console.error('Missing required env vars: PREVIEW_URL, SPACEPORT_EMAIL, SPACEPORT_PASSWORD, LITCHI_EMAIL, LITCHI_PASSWORD');
  process.exit(1);
}

const client = new Client({ name: 'spaceport-litchi-e2e', version: '1.0.0' }, { capabilities: {} });
const transport = new SSEClientTransport(new URL(SERVER_URL));
const steps = [];

function record(step, status, info = '') {
  const tag = status === 'pass' ? '✅' : status === 'warn' ? '⚠️' : '❌';
  steps.push({ step, status, info });
  const suffix = info ? ` — ${info}` : '';
  console.log(`${tag} ${step}${suffix}`);
}

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

function hasText(snapshot, text) {
  return new RegExp(escapeRegex(text), 'i').test(snapshot);
}

async function callTool(name, args, { silent } = {}) {
  const result = await client.callTool({ name, arguments: args });
  if (!silent) {
    const text = textFromResult(result);
    if (text) console.log(text);
  }
  return result;
}

async function waitForText(text, time = 20) {
  const result = await callTool('browser_wait_for', { text, time }, { silent: true });
  return snapshotFrom(result);
}

(async () => {
  await client.connect(transport);
  record('Connect MCP', 'pass', SERVER_URL);

  const targetUrl = `${PREVIEW_URL.replace(/\/$/, '')}/create`;
  const nav = await callTool('browser_navigate', { url: targetUrl }, { silent: true });
  let snapshot = snapshotFrom(nav);
  record('Navigate to create page', 'pass', targetUrl);

  const loginButtonRef = tryFindRef(snapshot, 'button', ['Login', 'Log in', 'Log In']);
  if (loginButtonRef) {
    await callTool('browser_click', { element: 'Login', ref: loginButtonRef }, { silent: true });
    record('Open login form', 'pass');
    await callTool('browser_wait_for', { text: 'Email', time: 15 }, { silent: true });
    snapshot = snapshotFrom(await callTool('browser_snapshot', {}, { silent: true }));
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
    }, { silent: true });
    record('Fill Spaceport credentials', 'pass', SPACEPORT_EMAIL);

    await callTool('browser_click', { element: 'Sign in', ref: signInRef }, { silent: true });
    record('Submit Spaceport login', 'pass');

    await callTool('browser_wait_for', { text: 'New Project', time: 30 }, { silent: true });
    snapshot = snapshotFrom(await callTool('browser_snapshot', {}, { silent: true }));
  } else {
    record('Login step', 'warn', 'Login form not detected; assuming already authenticated');
  }

  snapshot = snapshotFrom(await callTool('browser_snapshot', {}, { silent: true }));

  if (hasText(snapshot, 'Litchi Mission Control')) {
    const connected = hasText(snapshot, 'Connected') && hasText(snapshot, 'Litchi session connected');
    if (!connected) {
      const connectDashboardRef = tryFindRef(snapshot, 'button', ['Connect Litchi Account']);
      if (connectDashboardRef) {
        await callTool('browser_click', { element: 'Connect Litchi Account', ref: connectDashboardRef }, { silent: true });
        record('Open dashboard Litchi connect', 'pass');
        await callTool('browser_wait_for', { text: 'Connect Litchi Account', time: 20 }, { silent: true });
        snapshot = snapshotFrom(await callTool('browser_snapshot', {}, { silent: true }));

        const emailDialogRef = tryFindRef(snapshot, 'textbox', ['Email']);
        const passwordDialogRef = tryFindRef(snapshot, 'textbox', ['Password']);
        const connectDialogRef = tryFindRef(snapshot, 'button', ['Connect']);

        if (emailDialogRef && passwordDialogRef && connectDialogRef) {
          await callTool('browser_fill_form', {
            fields: [
              { name: 'Email', type: 'textbox', ref: emailDialogRef, value: LITCHI_EMAIL },
              { name: 'Password', type: 'textbox', ref: passwordDialogRef, value: LITCHI_PASSWORD }
            ]
          }, { silent: true });
          record('Fill Litchi credentials', 'pass', LITCHI_EMAIL);

          await callTool('browser_click', { element: 'Connect', ref: connectDialogRef }, { silent: true });
          record('Submit Litchi connect (dashboard)', 'pass');
          await callTool('browser_wait_for', { text: 'Connected', time: 60 }, { silent: true });
        } else {
          record('Fill Litchi credentials', 'fail', 'Connect dialog fields not found');
        }
      }
    }
  }

  const openHeadingRef = tryFindRef(snapshot, 'heading', ['New Project']);
  if (openHeadingRef) {
    await callTool('browser_click', { element: 'New Project', ref: openHeadingRef }, { silent: true });
  } else {
    await callTool('browser_evaluate', {
      function: '() => { const el = document.querySelector(".new-project-card"); if (!el) return false; el.click(); return true; }'
    }, { silent: true });
  }
  record('Open New Project modal', 'pass');

  await waitForText('Delivery & Automation', 20);
  snapshot = snapshotFrom(await callTool('browser_snapshot', {}, { silent: true }));

  if (!tryFindRef(snapshot, 'button', ['Send to Litchi']) && !tryFindRef(snapshot, 'button', ['Connect Litchi Account', 'Enter 2FA Code'])) {
    const newProjectRef = tryFindRef(snapshot, 'heading', ['New Project']);
    if (newProjectRef) {
      await callTool('browser_click', { element: 'New Project', ref: newProjectRef }, { silent: true });
      await callTool('browser_wait_for', { text: 'Delivery & Automation', time: 20 }, { silent: true });
    }
  }

  if (!tryFindRef(snapshot, 'button', ['Send to Litchi']) && !tryFindRef(snapshot, 'button', ['Connect Litchi Account', 'Enter 2FA Code'])) {
    const editRef = tryFindRef(snapshot, 'button', ['Edit project']);
    if (editRef) {
      await callTool('browser_click', { element: 'Edit project', ref: editRef }, { silent: true });
      await callTool('browser_wait_for', { text: 'Delivery & Automation', time: 20 }, { silent: true });
    }
  }

  snapshot = snapshotFrom(await callTool('browser_snapshot', {}, { silent: true }));

  let sendRef = tryFindRef(snapshot, 'button', ['Send to Litchi']);
  const connectRef = tryFindRef(snapshot, 'button', ['Connect Litchi Account', 'Enter 2FA Code']);

  if (!sendRef && connectRef) {
    await callTool('browser_click', { element: 'Connect Litchi Account', ref: connectRef }, { silent: true });
    record('Open Litchi connect form', 'pass');

    const inlineEmailRef = tryFindRef(snapshot, 'textbox', ['Email']);
    const inlinePasswordRef = tryFindRef(snapshot, 'textbox', ['Password']);
    if (inlineEmailRef && inlinePasswordRef) {
      await callTool('browser_fill_form', {
        fields: [
          { name: 'Email', type: 'textbox', ref: inlineEmailRef, value: LITCHI_EMAIL },
          { name: 'Password', type: 'textbox', ref: inlinePasswordRef, value: LITCHI_PASSWORD }
        ]
      }, { silent: true });
      record('Fill Litchi credentials', 'pass', LITCHI_EMAIL);
    }

    const inlineSubmitRef = tryFindRef(snapshot, 'button', ['Connect', 'Submit', 'Send']);
    if (inlineSubmitRef) {
      await callTool('browser_click', { element: 'Connect', ref: inlineSubmitRef }, { silent: true });
    }
    record('Submit Litchi connect', 'pass');

    await waitForText('Send to Litchi', 30);
    snapshot = snapshotFrom(await callTool('browser_snapshot', {}, { silent: true }));
    sendRef = tryFindRef(snapshot, 'button', ['Send to Litchi']);
  }

  if (!sendRef) {
    writeFileSync('logs/litchi-ui-missing-send.yaml', snapshot, 'utf-8');
    record('Litchi connection', 'fail', 'Send to Litchi button not found');
    process.exitCode = 1;
  } else {
    const locationRef = tryFindRef(snapshot, 'textbox', ['Enter location', 'Location', 'Address']);
    const durationRef = tryFindRef(snapshot, 'textbox', ['Duration']);
    const quantityRef = tryFindRef(snapshot, 'textbox', ['Quantity']);
    const mapRef = tryFindRef(snapshot, 'region', ['Map']);

    if (locationRef) {
      await callTool('browser_type', { element: 'Enter location', ref: locationRef, text: '38.27371, -78.1695', submit: true }, { silent: true });
      record('Set map coordinates', 'pass', '38.27371, -78.1695');
    } else {
      record('Set map coordinates', 'warn', 'Location input not found');
    }

    if (mapRef) {
      await callTool('browser_click', { element: 'Map', ref: mapRef }, { silent: true });
      record('Confirm map focus', 'pass');
    }

    if (durationRef && quantityRef) {
      await callTool('browser_fill_form', {
        fields: [
          { name: 'Duration', type: 'textbox', ref: durationRef, value: BATTERY_MINUTES },
          { name: 'Quantity', type: 'textbox', ref: quantityRef, value: BATTERY_COUNT }
        ]
      }, { silent: true });
      record('Set battery inputs', 'pass', `${BATTERY_MINUTES} min / ${BATTERY_COUNT} batteries`);
    } else {
      record('Set battery inputs', 'warn', 'Duration/Quantity inputs not found');
    }

    await callTool('browser_click', { element: 'Send to Litchi', ref: sendRef }, { silent: true });
    record('Trigger Send to Litchi', 'pass');

    const uploadSnapshot = await waitForText('Uploading', 120);
    if (hasText(uploadSnapshot, 'Please set battery quantity first')) {
      const okRef = tryFindRef(uploadSnapshot, 'button', ['OK']);
      if (okRef) {
        await callTool('browser_click', { element: 'OK', ref: okRef }, { silent: true });
      }
      if (durationRef && quantityRef) {
        await callTool('browser_fill_form', {
          fields: [
            { name: 'Duration', type: 'textbox', ref: durationRef, value: BATTERY_MINUTES },
            { name: 'Quantity', type: 'textbox', ref: quantityRef, value: BATTERY_COUNT }
          ]
        }, { silent: true });
      }
      await callTool('browser_click', { element: 'Send to Litchi', ref: sendRef }, { silent: true });
    }

    const started = /Uploading|Litchi upload started|Queued/i.test(uploadSnapshot);
    record('Confirm upload started', started ? 'pass' : 'warn');
  }

  console.log('\nSummary:', JSON.stringify(steps, null, 2));
  await client.close();
})();
