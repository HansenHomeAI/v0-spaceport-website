#!/usr/bin/env node
import { Client } from '@modelcontextprotocol/sdk/client';
import { SSEClientTransport } from '@modelcontextprotocol/sdk/client/sse.js';
import { execSync } from 'node:child_process';

const CLIENT_ID = '4jqu6jc4nl6rt7jih7l12071p';

const PREVIEW_URL = process.argv[2] ?? process.env.PREVIEW_URL;
const EMAIL = process.argv[3] ?? process.env.TEST_EMAIL;
const PASSWORD = process.argv[4] ?? process.env.TEST_PASSWORD;

if (!PREVIEW_URL || !EMAIL || !PASSWORD) {
  console.error('Usage: check_dashboard_plan.mjs <preview-url> <email> <password>');
  process.exit(1);
}

const client = new Client({ name: 'dashboard-plan-check', version: '1.0.0' }, { capabilities: {} });
const transport = new SSEClientTransport(new URL(process.env.PLAYWRIGHT_MCP_SSE_URL ?? 'http://127.0.0.1:5174/sse'));

function fetchTokens() {
  const command = `aws cognito-idp initiate-auth --region us-west-2 --auth-flow USER_PASSWORD_AUTH --client-id ${CLIENT_ID} --auth-parameters USERNAME=${EMAIL},PASSWORD=${PASSWORD}`;
  const raw = execSync(command, { stdio: ['ignore', 'pipe', 'inherit'] }).toString();
  return JSON.parse(raw).AuthenticationResult;
}

function decodeUsername(idToken) {
  const base64 = idToken.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
  const json = Buffer.from(base64, 'base64').toString('utf8');
  const payload = JSON.parse(json);
  return payload['cognito:username'] || payload['sub'];
}

async function primeSession(tokens, username) {
  await client.callTool({ name: 'browser_navigate', arguments: { url: PREVIEW_URL } });
  await client.callTool({
    name: 'browser_evaluate',
    arguments: {
      function: `() => {
        const clientId = '${CLIENT_ID}';
        const username = '${username}';
        const baseKey = 'CognitoIdentityServiceProvider.' + clientId;
        localStorage.setItem(baseKey + '.LastAuthUser', username);
        localStorage.setItem(baseKey + '.' + username + '.idToken', '${tokens.IdToken}');
        localStorage.setItem(baseKey + '.' + username + '.accessToken', '${tokens.AccessToken}');
        localStorage.setItem(baseKey + '.' + username + '.refreshToken', '${tokens.RefreshToken}');
      }`
    }
  });
  await client.callTool({ name: 'browser_navigate', arguments: { url: `${PREVIEW_URL.replace(/\/$/, '')}/create` } });
  await client.callTool({ name: 'browser_wait_for', arguments: { url_contains: '/create', time: 10 } });
  await client.callTool({ name: 'browser_wait_for', arguments: { text: 'Dashboard', time: 5 } });
}

async function readPlan() {
  const result = await client.callTool({
    name: 'browser_evaluate',
    arguments: {
      function: `() => {
        const planEl = document.querySelector('.subscription-pill');
        const modelsEl = document.querySelector('.model-count');
        return {
          plan: planEl ? planEl.textContent.trim() : null,
          models: modelsEl ? modelsEl.textContent.trim() : null,
          url: window.location.href
        };
      }`
    }
  });
  const payload = result?.content?.[0]?.text ?? '';
  console.log(payload);
}

(async () => {
  await client.connect(transport);
  const tokens = fetchTokens();
  const username = decodeUsername(tokens.IdToken);
  await primeSession(tokens, username);
  await readPlan();
  await client.close();
})();
