'use client';
import { Amplify } from 'aws-amplify';

let configured = false;
let available = false;

export function configureAmplify(): boolean {
  if (configured) return;
  // Prefer env, but fall back to deployed pool/client so sign-in is never blocked in prod
  const region = process.env.NEXT_PUBLIC_COGNITO_REGION || 'us-west-2';
  // IMPORTANT: do not default to development pool in production. Require explicit env variables.
  const userPoolId = process.env.NEXT_PUBLIC_COGNITO_USER_POOL_ID || '';
  const userPoolWebClientId = process.env.NEXT_PUBLIC_COGNITO_USER_POOL_CLIENT_ID || '';

  if (!region || !userPoolId || !userPoolWebClientId) {
    // Leave unconfigured in dev if not provided
    configured = true;
    available = false;
    return false;
  }

  Amplify.configure({
    Auth: {
      region,
      userPoolId,
      userPoolWebClientId,
      mandatorySignIn: false,
      loginWith: { // support email and username sign-in if enabled
        username: true,
        email: true,
      }
    },
    ssr: true,
  } as any);
  // Expose Projects API URL for client calls (must be provided via env by environment)
  const apiUrl = process.env.NEXT_PUBLIC_PROJECTS_API_URL;
  if (apiUrl) {
    (globalThis as any).NEXT_PUBLIC_PROJECTS_API_URL = apiUrl;
  }
  configured = true;
  available = true;
  return true;
}

export function isAuthAvailable(): boolean {
  return available;
}


