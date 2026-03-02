#!/usr/bin/env node
/**
 * Test sign-in and projects fetch with staging Cognito + APIs.
 * Usage: node --env-file=.env.local scripts/test-auth-and-projects.mjs
 * Or:    TEST_EMAIL=... TEST_PASSWORD=... node --env-file=.env.local scripts/test-auth-and-projects.mjs
 */

const EMAIL = process.env.TEST_EMAIL;
const PASSWORD = process.env.TEST_PASSWORD;
if (!EMAIL || !PASSWORD) {
  console.error('Set TEST_EMAIL and TEST_PASSWORD env vars');
  process.exit(1);
}

const REGION = process.env.NEXT_PUBLIC_COGNITO_REGION;
const USER_POOL_ID = process.env.NEXT_PUBLIC_COGNITO_USER_POOL_ID;
const CLIENT_ID = process.env.NEXT_PUBLIC_COGNITO_USER_POOL_CLIENT_ID;
const PROJECTS_URL = process.env.NEXT_PUBLIC_PROJECTS_API_URL;
const SUBSCRIPTION_BASE = process.env.NEXT_PUBLIC_SUBSCRIPTION_API_URL;

async function main() {
  console.log('Config:', {
    REGION: REGION ? '✓' : '✗',
    USER_POOL_ID: USER_POOL_ID ? '✓' : '✗',
    CLIENT_ID: CLIENT_ID ? '✓' : '✗',
    PROJECTS_URL: PROJECTS_URL || '✗',
    SUBSCRIPTION_BASE: SUBSCRIPTION_BASE ? '✓' : '✗',
  });
  if (!REGION || !USER_POOL_ID || !CLIENT_ID || !PROJECTS_URL) {
    console.error('Missing env vars. Ensure .env.local is loaded.');
    process.exit(1);
  }

  // Use Amplify Auth (same as app)
  const { Amplify } = await import('aws-amplify');
  Amplify.configure({
    Auth: {
      region: REGION,
      userPoolId: USER_POOL_ID,
      userPoolWebClientId: CLIENT_ID,
    },
  });

  const { Auth } = await import('aws-amplify');

  console.log('\n1. Signing in...');
  let idToken;
  try {
    const res = await Auth.signIn(EMAIL, PASSWORD);
    if (res.challengeName === 'NEW_PASSWORD_REQUIRED') {
      console.error('Account requires new password. Complete setup in browser first.');
      process.exit(1);
    }
    const session = await Auth.currentSession();
    idToken = session.getIdToken().getJwtToken();
    console.log('   Sign-in OK');
  } catch (err) {
    console.error('   Sign-in failed:', err.message);
    process.exit(1);
  }

  console.log('\n2. Fetching projects...');
  const projRes = await fetch(PROJECTS_URL, {
    headers: { Authorization: `Bearer ${idToken}` },
  });
  console.log('   Projects API status:', projRes.status, projRes.statusText);
  if (!projRes.ok) {
    const text = await projRes.text();
    console.error('   Response:', text.slice(0, 500));
    process.exit(1);
  }
  const projData = await projRes.json();
  const projects = projData.projects || [];
  console.log('   Projects count:', projects.length);
  if (projects.length > 0) {
    console.log('   First project:', projects[0].title || projects[0].projectId);
  }

  if (SUBSCRIPTION_BASE) {
    const subUrl = `${SUBSCRIPTION_BASE.replace(/\/$/, '')}/subscription/subscription-status`;
    console.log('\n3. Fetching subscription status...');
    const subRes = await fetch(subUrl, {
      headers: { Authorization: `Bearer ${idToken}` },
    });
    console.log('   Subscription API status:', subRes.status, subRes.statusText);
    if (subRes.ok) {
      const subData = await subRes.json();
      console.log('   Subscription:', subData.subscription?.status || subData);
    } else {
      console.log('   Response:', await subRes.text().then((t) => t.slice(0, 300)));
    }
  }

  console.log('\n✓ Auth and projects test passed.');
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
