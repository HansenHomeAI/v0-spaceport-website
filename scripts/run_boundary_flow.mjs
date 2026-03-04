#!/usr/bin/env node
import { Client } from '@modelcontextprotocol/sdk/client';
import { SSEClientTransport } from '@modelcontextprotocol/sdk/client/sse.js';

const SERVER_URL = process.env.PLAYWRIGHT_MCP_SSE_URL ?? 'http://localhost:5174/sse';
const BASE_URL = process.argv[2] ?? process.env.PREVIEW_URL ?? 'http://localhost:3000';
const TARGET_URL = `${BASE_URL.replace(/\/$/, '')}/create`;
const SCREENSHOT_PATH = process.env.BOUNDARY_FLOW_SCREENSHOT ?? 'logs/boundary-flow.png';
const EMAIL = process.env.TEST_EMAIL;
const PASSWORD = process.env.TEST_PASSWORD;

const client = new Client(
  { name: 'spaceport-boundary-flow', version: '1.0.0' },
  { capabilities: {} }
);

const transport = new SSEClientTransport(new URL(SERVER_URL));

function extractText(result) {
  return result?.content?.find((entry) => entry.type === 'text')?.text ?? '';
}

async function callTool(name, args) {
  return await client.callTool({ name, arguments: args });
}

function logLine(step, status, info = '') {
  const suffix = info ? ` - ${info}` : '';
  console.log(`[${status}] ${step}${suffix}`);
}

async function main() {
  if (!EMAIL || !PASSWORD) {
    logLine('Boundary flow', 'WARN', 'TEST_EMAIL and TEST_PASSWORD are required; skipping scripted login flow');
    return;
  }

  try {
    await client.connect(transport);
    logLine('Connect to MCP server', 'PASS', SERVER_URL);

    await callTool('browser_navigate', { url: TARGET_URL });
    await callTool('browser_wait_for', { text: 'Login', time: 10 });
    logLine('Navigate', 'PASS', TARGET_URL);

    await callTool('browser_run_code', {
      code: `async (page) => {
        await page.getByRole('button', { name: 'Login' }).click();
        await page.getByPlaceholder(/email/i).fill(${JSON.stringify(EMAIL)});
        await page.getByPlaceholder(/password/i).fill(${JSON.stringify(PASSWORD)});
        await page.getByRole('button', { name: 'Sign in' }).click();

        const saveAndSignIn = page.getByRole('button', { name: 'Save and sign in' });
        const newPasswordInput = page.getByPlaceholder(/new password/i);
        const needsPassword = await newPasswordInput
          .waitFor({ state: 'visible', timeout: 10000 })
          .then(() => true)
          .catch(() => false);

        if (needsPassword) {
          const suffix = Date.now().toString().slice(-4);
          await newPasswordInput.fill(\`Boundary\${suffix}Aa!\`);
          await page.getByPlaceholder(/handle/i).fill(\`boundary\${Date.now()}\`);
          await saveAndSignIn.click();
          await saveAndSignIn.waitFor({ state: 'hidden', timeout: 20000 });
        }

        await page.getByText('New Project').waitFor({ state: 'visible', timeout: 20000 });
        await page.locator('.new-project-card').click();
        await page.locator('#address-search').fill('39.739200, -104.990300');
        await page.locator('#address-search').press('Enter');
        await page.getByPlaceholder('Duration').fill('20');
        await page.getByPlaceholder('Quantity').fill('3');
        await page.click('#expand-button');
        await page.getByRole('button', { name: 'Boundary' }).click();
        await page.locator('.boundary-editor-bar').waitFor({ state: 'visible', timeout: 20000 });

        const dragHandle = async (selector, dx, dy) => {
          const box = await page.locator(selector).boundingBox();
          if (!box) throw new Error(\`Missing boundary handle: \${selector}\`);
          const x = box.x + box.width / 2;
          const y = box.y + box.height / 2;
          await page.mouse.move(x, y);
          await page.mouse.down();
          await page.mouse.move(x + dx, y + dy, { steps: 12 });
          await page.mouse.up();
        };

        await dragHandle('.boundary-handle-marker.major', 90, -24);
        await dragHandle('.boundary-handle-marker.minor', 0, 55);
        await page.getByRole('button', { name: 'Apply' }).click();
        await page.locator('.boundary-handle-marker.major').waitFor({ state: 'visible', timeout: 20000 });
        return 'boundary flow complete';
      }`,
    });
    logLine('Boundary editor flow', 'PASS');

    await callTool('browser_take_screenshot', { type: 'png', filename: SCREENSHOT_PATH });
    logLine('Screenshot', 'PASS', SCREENSHOT_PATH);

    const consoleResult = await callTool('browser_console_messages', { level: 'error' });
    const consoleText = extractText(consoleResult).trim();
    const zeroMessages =
      /Returning 0 messages/i.test(consoleText) ||
      /Total messages:\s*0\b/i.test(consoleText);
    if (!consoleText || zeroMessages) {
      logLine('Console errors', 'PASS', 'none');
    } else {
      logLine('Console errors', 'FAIL', 'See stderr output');
      console.error(consoleText);
      process.exitCode = 1;
    }
  } catch (error) {
    logLine('Boundary flow failed', 'FAIL', error?.message ?? String(error));
    process.exitCode = 1;
  } finally {
    await client.close().catch(() => {});
  }
}

await main();
