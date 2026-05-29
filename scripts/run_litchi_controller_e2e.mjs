#!/usr/bin/env node
import { chromium } from 'playwright';
import { mkdirSync, writeFileSync } from 'node:fs';
import path from 'node:path';

const PREVIEW_URL = process.env.PREVIEW_URL;
const SPACEPORT_EMAIL = process.env.SPACEPORT_EMAIL;
const SPACEPORT_PASSWORD = process.env.SPACEPORT_PASSWORD;
const LITCHI_API_URL = process.env.LITCHI_API_URL;
const RUN_DIR = process.env.LITCHI_E2E_DIR || `logs/litchi-e2e-${new Date().toISOString().replace(/[:.]/g, '-')}`;
const PROJECT_TITLE = process.env.LITCHI_PROJECT_TITLE || `litchi-e2e-${new Date().toISOString().slice(0, 19).replace(/[-:T]/g, '')}`;
const LOCATION = process.env.LITCHI_LOCATION || '38.27371, -78.16950';
const BATTERY_MINUTES = process.env.LITCHI_BATTERY_MINUTES || '10';
const BATTERY_COUNT = process.env.LITCHI_BATTERY_COUNT || '1';
const MIN_ALTITUDE = process.env.LITCHI_MIN_ALTITUDE || '120';
const MAX_ALTITUDE = process.env.LITCHI_MAX_ALTITUDE || '160';
const PLAYWRIGHT_CHANNEL = process.env.PLAYWRIGHT_CHANNEL || 'chrome';

if (!PREVIEW_URL || !SPACEPORT_EMAIL || !SPACEPORT_PASSWORD || !LITCHI_API_URL) {
  console.error('Missing env vars: PREVIEW_URL, SPACEPORT_EMAIL, SPACEPORT_PASSWORD, LITCHI_API_URL');
  process.exit(1);
}

mkdirSync(RUN_DIR, { recursive: true });

const events = [];
const network = [];
const consoleMessages = [];

function log(step, data = {}) {
  const entry = { at: new Date().toISOString(), step, ...data };
  events.push(entry);
  console.log(JSON.stringify(entry));
}

function redacted(value) {
  if (!value) return value;
  return String(value).replace(/(.{2}).*(@.*)/, '$1***$2');
}

async function shot(page, name) {
  const file = path.join(RUN_DIR, `${name}.png`);
  await page.screenshot({ path: file, fullPage: false });
  return file;
}

async function clickVisible(page, names, scopeSelector = null) {
  const scope = scopeSelector ? page.locator(scopeSelector).first() : page;
  for (const name of names) {
    const locator = scope.getByRole('button', { name: new RegExp(name, 'i') }).first();
    if (await locator.count()) {
      try {
        await locator.click();
      } catch (error) {
        await locator.evaluate((button) => button.click());
        log('dom-click-fallback', { name, reason: error.message.split('\n')[0] });
      }
      return name;
    }
  }
  for (const name of names) {
    const locator = scope.getByText(new RegExp(name, 'i')).first();
    if (await locator.count()) {
      await locator.click();
      return name;
    }
  }
  throw new Error(`No visible control found for ${names.join(' / ')}`);
}

async function fillByPlaceholder(page, placeholder, value) {
  const input = page.getByPlaceholder(placeholder).first();
  await input.waitFor({ state: 'visible', timeout: 30000 });
  await input.click({ clickCount: 3 });
  await input.fill(value);
  return input;
}

async function currentIdToken(page) {
  return page.evaluate(() => {
    for (const key of Object.keys(localStorage)) {
      if (key.includes('idToken')) return localStorage.getItem(key);
    }
    return null;
  });
}

async function fetchStatus(page) {
  const token = await currentIdToken(page);
  if (!token) throw new Error('No Cognito id token found after sign-in');
  return page.evaluate(async ({ base, jwt }) => {
    const response = await fetch(`${base.replace(/\/$/, '')}/litchi/status`, {
      headers: { Authorization: `Bearer ${jwt}`, 'Content-Type': 'application/json' },
    });
    const text = await response.text();
    return {
      ok: response.ok,
      status: response.status,
      body: text ? JSON.parse(text) : null,
    };
  }, { base: LITCHI_API_URL, jwt: token });
}

async function main() {
  const browser = await chromium.launch({ headless: true, channel: PLAYWRIGHT_CHANNEL });
  const context = await browser.newContext({
    viewport: { width: 1366, height: 900 },
    deviceScaleFactor: 1,
  });
  const page = await context.newPage();

  page.on('console', (msg) => {
    const text = msg.text();
    consoleMessages.push({ type: msg.type(), text });
  });
  page.on('response', async (response) => {
    const url = response.url();
    if (/\/litchi\/|\/api\/csv\/battery|\/api\/optimize-spiral|\/api\/elevation/.test(url)) {
      network.push({ url, status: response.status(), method: response.request().method() });
    }
  });

  const target = `${PREVIEW_URL.replace(/\/$/, '')}/create`;
  await page.goto(target, { waitUntil: 'domcontentloaded' });
  log('opened-create-page', { url: target });

  await page.waitForTimeout(2000);
  const loginButton = page.getByRole('button', { name: /log in|login|sign in/i }).first();
  if (await loginButton.count()) {
    await loginButton.click();
  }

  const emailInput = page.locator('input[type="email"], input[name*="email" i], input[placeholder*="email" i]').first();
  if (await emailInput.count()) {
    await emailInput.fill(SPACEPORT_EMAIL);
    await page.locator('input[type="password"]').first().fill(SPACEPORT_PASSWORD);
    await clickVisible(page, ['sign in', 'log in', 'login']);
    log('submitted-spaceport-login', { email: redacted(SPACEPORT_EMAIL) });
    await page.waitForFunction(() => {
      const hasToken = Object.keys(localStorage).some((key) => key.includes('idToken'));
      const text = document.body.innerText || '';
      if (/incorrect|failed|not authorized|error/i.test(text)) return 'login-error';
      return hasToken;
    }, null, { timeout: 60000 });
  }

  await page.waitForFunction(() => Object.keys(localStorage).some((key) => key.includes('idToken')), null, { timeout: 60000 });
  await page.getByText(/Dashboard|New Project/i).first().waitFor({ timeout: 60000 });
  await shot(page, '01-dashboard-signed-in');
  log('spaceport-signed-in');

  let statusBefore = await fetchStatus(page);
  const readyDeadline = Date.now() + 5 * 60 * 1000;
  while (statusBefore.body?.status === 'uploading' && Date.now() < readyDeadline) {
    log('waiting-for-existing-controller-upload', {
      message: statusBefore.body?.message,
      progress: statusBefore.body?.progress,
    });
    await page.waitForTimeout(10000);
    statusBefore = await fetchStatus(page);
  }
  writeFileSync(path.join(RUN_DIR, 'status-before.json'), JSON.stringify(statusBefore, null, 2));
  if (!statusBefore.ok || !statusBefore.body?.connected) {
    throw new Error(`Cached Litchi controller session is not connected: ${JSON.stringify(statusBefore.body)}`);
  }
  log('litchi-session-connected', {
    status: statusBefore.body.status,
    sessionCached: statusBefore.body.sessionCached,
    message: statusBefore.body.message,
  });

  await clickVisible(page, ['New Project', 'Create Project', 'Create New Project']);
  await page.locator('#newProjectPopup').waitFor({ state: 'visible', timeout: 30000 });
  await page.locator('#projectTitle').fill(PROJECT_TITLE);
  await shot(page, '02-new-project-open');
  log('opened-flight-plan-modal', { projectTitle: PROJECT_TITLE });

  const locationInput = page.getByPlaceholder('Enter location').first();
  await locationInput.waitFor({ state: 'visible', timeout: 30000 });
  await locationInput.click({ clickCount: 3 });
  await locationInput.press(process.platform === 'darwin' ? 'Meta+A' : 'Control+A');
  await locationInput.type(LOCATION, { delay: 20 });
  await page.waitForTimeout(300);
  await locationInput.press('Enter');
  await page.waitForTimeout(3000);
  const mapBox = await page.locator('#map-container').boundingBox();
  if (mapBox) {
    await page.mouse.click(mapBox.x + mapBox.width / 2, mapBox.y + mapBox.height / 2);
  }
  await fillByPlaceholder(page, 'Duration', BATTERY_MINUTES);
  await fillByPlaceholder(page, 'Quantity', BATTERY_COUNT);
  await fillByPlaceholder(page, 'Minimum', MIN_ALTITUDE);
  await fillByPlaceholder(page, 'Maximum', MAX_ALTITUDE);
  log('configured-flight-plan', {
    location: LOCATION,
    batteries: BATTERY_COUNT,
    minutes: BATTERY_MINUTES,
    altitude: `${MIN_ALTITUDE}-${MAX_ALTITUDE}`,
  });

  await page.locator('.popup-content-scroll').evaluate((el) => { el.scrollTop = el.scrollHeight; });
  await page.getByText('Delivery & Automation').waitFor({ timeout: 20000 });
  await shot(page, '03-delivery-section');

  await clickVisible(page, ['Select all'], '#newProjectPopup');
  await page.waitForTimeout(500);
  const names = await page.locator('.litchi-name-preview span').evaluateAll((els) =>
    els.map((el) => el.textContent?.trim()).filter(Boolean)
  );
  if (!names.length) throw new Error('No controller mission names appeared after selecting flight files');
  writeFileSync(path.join(RUN_DIR, 'mission-names.json'), JSON.stringify(names, null, 2));
  log('captured-controller-mission-names', { names });

  await shot(page, '04-ready-to-send');
  await clickVisible(page, ['Send to Controller', 'Send \\d+ files to Controller'], '#newProjectPopup');
  log('clicked-send-to-controller');

  const uploadPostDeadline = Date.now() + 60000;
  while (
    Date.now() < uploadPostDeadline
    && !network.some((entry) => /\/litchi\/upload/.test(entry.url) && entry.method === 'POST')
  ) {
    await page.waitForTimeout(1000);
  }
  await shot(page, '05-after-send-click');
  const uploadPosted = network.some((entry) => /\/litchi\/upload/.test(entry.url) && entry.method === 'POST');
  if (!uploadPosted) {
    throw new Error('Send to Controller did not POST /litchi/upload; check location selection and button hit target.');
  }
  const statusAfterClick = await fetchStatus(page);
  writeFileSync(path.join(RUN_DIR, 'status-after-click.json'), JSON.stringify(statusAfterClick, null, 2));
  log('spaceport-status-after-click', {
    status: statusAfterClick.body?.status,
    message: statusAfterClick.body?.message,
    progress: statusAfterClick.body?.progress,
  });

  let finalStatus = statusAfterClick;
  const deadline = Date.now() + 10 * 60 * 1000;
  while (Date.now() < deadline) {
    finalStatus = await fetchStatus(page);
    const logs = finalStatus.body?.logs || [];
    const uploaded = names.every((name) => logs.some((entry) => entry.includes(`Uploaded ${name}`)));
    if (uploaded) break;
    if (finalStatus.body?.status === 'error' || finalStatus.body?.status === 'expired') {
      throw new Error(`Litchi upload failed: ${finalStatus.body?.message}`);
    }
    await page.waitForTimeout(10000);
  }
  writeFileSync(path.join(RUN_DIR, 'status-final.json'), JSON.stringify(finalStatus, null, 2));
  const finalLogs = finalStatus.body?.logs || [];
  const uploadedAll = names.every((name) => finalLogs.some((entry) => entry.includes(`Uploaded ${name}`)));
  if (!uploadedAll) {
    throw new Error(`Timed out waiting for uploaded logs for ${names.join(', ')}`);
  }
  log('spaceport-confirmed-uploaded', {
    status: finalStatus.body.status,
    message: finalStatus.body.message,
    progress: finalStatus.body.progress,
  });

  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(1000);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.locator('#newProjectPopup').waitFor({ state: 'visible', timeout: 10000 }).catch(() => {});
  await shot(page, '06-mobile-responsive-check');
  const mobileMetrics = await page.evaluate(() => ({
    innerWidth: window.innerWidth,
    documentScrollWidth: document.documentElement.scrollWidth,
    overflowingElements: Array.from(document.querySelectorAll('button, input, textarea, .litchi-card-header, .litchi-actions, .litchi-name-preview'))
      .filter((el) => el.getBoundingClientRect().right > window.innerWidth + 2)
      .map((el) => ({ tag: el.tagName, text: (el.textContent || el.getAttribute('placeholder') || '').trim().slice(0, 80) })),
  }));
  writeFileSync(path.join(RUN_DIR, 'mobile-metrics.json'), JSON.stringify(mobileMetrics, null, 2));
  log('mobile-responsive-check', mobileMetrics);

  writeFileSync(path.join(RUN_DIR, 'network.json'), JSON.stringify(network, null, 2));
  writeFileSync(path.join(RUN_DIR, 'console.json'), JSON.stringify(consoleMessages, null, 2));
  writeFileSync(path.join(RUN_DIR, 'events.json'), JSON.stringify(events, null, 2));
  await browser.close();

  console.log(JSON.stringify({
    ok: true,
    runDir: RUN_DIR,
    projectTitle: PROJECT_TITLE,
    missionNames: names,
    status: finalStatus.body,
  }, null, 2));
}

main().catch((error) => {
  writeFileSync(path.join(RUN_DIR, 'events.json'), JSON.stringify(events, null, 2));
  writeFileSync(path.join(RUN_DIR, 'network.json'), JSON.stringify(network, null, 2));
  writeFileSync(path.join(RUN_DIR, 'console.json'), JSON.stringify(consoleMessages, null, 2));
  console.error(error);
  process.exit(1);
});
