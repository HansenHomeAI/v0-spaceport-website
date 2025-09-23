#!/usr/bin/env node
import { Client } from '@modelcontextprotocol/sdk/client';
import { SSEClientTransport } from '@modelcontextprotocol/sdk/client/sse.js';

const SERVER_URL = process.env.PLAYWRIGHT_MCP_SSE_URL ?? 'http://127.0.0.1:5174/sse';
const PREVIEW_URL = process.argv[2] ?? process.env.PREVIEW_URL;
const EMAIL = process.argv[3] ?? process.env.TEST_EMAIL;
const PASSWORD = process.argv[4] ?? process.env.TEST_PASSWORD;
const PLAN = process.argv[5] ?? 'single';

if (!PREVIEW_URL || !EMAIL || !PASSWORD) {
  console.error('Usage: run_full_subscription_flow.mjs <preview-url> <email> <password> [plan]');
  process.exit(1);
}

const CARD = process.env.TEST_CARD ?? '4242424242424242';
const EXP = process.env.TEST_EXP ?? '1234'; // MMYY typed without slash
const CVC = process.env.TEST_CVC ?? '123';
const ZIP = process.env.TEST_ZIP ?? '90210';

const client = new Client({ name: 'spaceport-subscription-e2e', version: '1.0.0' }, { capabilities: {} });
const transport = new SSEClientTransport(new URL(SERVER_URL));

const steps = [];
function record(step, status, info = '') {
  const tag = status === 'pass' ? '✅' : status === 'warn' ? '⚠️' : '❌';
  steps.push({ step, status, info });
  const suffix = info ? ` — ${info}` : '';
  console.log(`${tag} ${step}${suffix}`);
}

async function callTool(name, args, { silent } = {}) {
  const result = await client.callTool({ name, arguments: args });
  if (!silent) {
    const text = result?.content?.find(c => c.type === 'text')?.text;
    if (text) {
      console.log(text);
    }
  }
  return result;
}

function parseSnapshot(result) {
  const text = result?.content?.find(c => c.type === 'text')?.text ?? '';
  const match = text.match(/Page Snapshot:\n```yaml\n([\s\S]*?)```/);
  return match ? match[1] : '';
}

async function assertField(ref, label, expected) {
  const result = await callTool('browser_evaluate', { ref, function: 'el => el.value' }, { silent: true });
  const valueLine = result?.content?.[0]?.text?.split('\n')?.[1]?.trim();
  const ok = valueLine?.replace(/^"|"$/g, '') === expected;
  record(`Confirm ${label}`, ok ? 'pass' : 'warn', ok ? expected : valueLine ?? '');
}

(async () => {
  await client.connect(transport);
  record('Connect MCP', 'pass', SERVER_URL);

  const authUrl = `${PREVIEW_URL.replace(/\/$/, '')}/auth?redirect=pricing&plan=${PLAN}`;
  const navigate = await callTool('browser_navigate', { url: authUrl });
  parseSnapshot(navigate); // ensures we have refs cached
  record('Open auth page', 'pass', authUrl);

  await callTool('browser_fill_form', {
    fields: [
      { name: 'Email', type: 'textbox', ref: 'e31', value: EMAIL },
      { name: 'Password', type: 'textbox', ref: 'e33', value: PASSWORD }
    ]
  }, { silent: true });
  record('Fill credentials', 'pass', EMAIL);

  await callTool('browser_click', { element: 'Sign in', ref: 'e38' }, { silent: true });
  record('Submit sign-in', 'pass');

  await callTool('browser_wait_for', { url_contains: 'checkout.stripe.com', time: 30 }, { silent: true });
  const stripeLocation = await callTool('browser_evaluate', { function: '() => window.location.href' }, { silent: true });
  const stripeUrl = stripeLocation?.content?.[0]?.text?.split('\n')?.[1]?.trim()?.replace(/^"|"$/g, '') ?? '';
  record('Arrive at Stripe', 'pass', stripeUrl);

  await callTool('browser_click', { element: 'Email', ref: 'e74' }, { silent: true });
  await callTool('browser_type', { element: 'Email', ref: 'e74', text: EMAIL }, { silent: true });
  await assertField('e74', 'email', EMAIL);

  await callTool('browser_click', { element: 'Card number', ref: 'e116' }, { silent: true });
  await callTool('browser_type', { element: 'Card number', ref: 'e116', text: CARD, slowly: true }, { silent: true });
  await assertField('e116', 'card number', CARD.replace(/\s/g, ''));

  await callTool('browser_click', { element: 'Expiration', ref: 'e121' }, { silent: true });
  await callTool('browser_type', { element: 'Expiration', ref: 'e121', text: EXP, slowly: true }, { silent: true });
  await assertField('e121', 'expiration', EXP);

  await callTool('browser_click', { element: 'CVC', ref: 'e126' }, { silent: true });
  await callTool('browser_type', { element: 'CVC', ref: 'e126', text: CVC }, { silent: true });
  await assertField('e126', 'cvc', CVC);

  await callTool('browser_click', { element: 'ZIP', ref: 'e159' }, { silent: true });
  await callTool('browser_type', { element: 'ZIP', ref: 'e159', text: ZIP }, { silent: true });
  await assertField('e159', 'zip', ZIP);

  record('Fill payment details', 'pass');

  await callTool('browser_click', { element: 'Subscribe', ref: 'e218' }, { silent: true });
  record('Submit payment', 'pass');

  await callTool('browser_wait_for', { url_contains: 'subscription=success', time: 60 }, { silent: true });
  const successLocation = await callTool('browser_evaluate', { function: '() => window.location.href' }, { silent: true });
  const successUrl = successLocation?.content?.[0]?.text?.split('\n')?.[1]?.trim()?.replace(/^"|"$/g, '') ?? '';
  record('Receive success redirect', successUrl.includes('subscription=success') ? 'pass' : 'warn', successUrl);

  console.log('\nSummary:', JSON.stringify(steps, null, 2));
  await client.close();
})();
