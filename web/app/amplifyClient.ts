'use client';
import { Amplify } from 'aws-amplify';

let configured = false;
let available = false;

export function configureAmplify(): boolean {
  if (configured) return;
  // Prefer env, but fall back to deployed pool/client so sign-in is never blocked in prod
  const region = process.env.NEXT_PUBLIC_COGNITO_REGION || 'us-west-2';
  const userPoolId = process.env.NEXT_PUBLIC_COGNITO_USER_POOL_ID || 'us-west-2_a2jf3ldGV';
  const userPoolWebClientId = process.env.NEXT_PUBLIC_COGNITO_USER_POOL_CLIENT_ID || '3ctkuqu98pmug5k5kgc119sq67';

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
  configured = true;
  available = true;
  return true;
}

export function isAuthAvailable(): boolean {
  return available;
}


