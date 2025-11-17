'use client';
import { Amplify } from 'aws-amplify';

let configured = false;
let available = false;

function removeMismatchedCognitoTokens(expectedIssuer: string): void {
  if (typeof window === 'undefined') return;
  try {
    const isJwt = (v: string) => typeof v === 'string' && v.split('.').length === 3;
    const decode = (s: string) => {
      const pad = s.length % 4;
      if (pad) s = s + '='.repeat(4 - pad);
      return JSON.parse(atob(s.replace(/-/g, '+').replace(/_/g, '/')));
    };

    const keysToRemove: string[] = [];
    for (let i = 0; i < window.localStorage.length; i++) {
      const key = window.localStorage.key(i);
      if (!key) continue;
      if (!key.startsWith('CognitoIdentityServiceProvider.')) continue;
      const val = window.localStorage.getItem(key) || '';
      // Stored as JSON with idToken/accessToken OR a raw token
      if (isJwt(val)) {
        try {
          const payload = decode(val.split('.')[1]);
          if (payload?.iss && payload.iss !== expectedIssuer) keysToRemove.push(key);
        } catch {}
        continue;
      }
      try {
        const obj = JSON.parse(val);
        for (const maybeToken of Object.values(obj)) {
          if (typeof maybeToken === 'string' && isJwt(maybeToken)) {
            try {
              const payload = decode(maybeToken.split('.')[1]);
              if (payload?.iss && payload.iss !== expectedIssuer) {
                keysToRemove.push(key);
                break;
              }
            } catch {}
          }
        }
      } catch {}
    }
    keysToRemove.forEach(k => window.localStorage.removeItem(k));
  } catch {}
}

export function configureAmplify(): boolean {
  if (configured) return available;

  const region = process.env.NEXT_PUBLIC_COGNITO_REGION || '';
  const userPoolId = process.env.NEXT_PUBLIC_COGNITO_USER_POOL_ID || '';
  const userPoolWebClientId = process.env.NEXT_PUBLIC_COGNITO_USER_POOL_CLIENT_ID || '';

  if (!region || !userPoolId || !userPoolWebClientId) {
    configured = true;
    available = false;
    return false;
  }

  // Defensive: purge any tokens in storage that don't match the configured pool
  const expectedIssuer = `https://cognito-idp.${region}.amazonaws.com/${userPoolId}`;
  removeMismatchedCognitoTokens(expectedIssuer);

  Amplify.configure({
    Auth: {
      region,
      userPoolId,
      userPoolWebClientId,
      mandatorySignIn: false,
      loginWith: {
        username: true,
        email: true,
      }
    },
    ssr: true,
  } as any);

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
