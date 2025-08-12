'use client';
import { Amplify } from 'aws-amplify';

let configured = false;

export function configureAmplify(): void {
  if (configured) return;
  const region = process.env.NEXT_PUBLIC_COGNITO_REGION;
  const userPoolId = process.env.NEXT_PUBLIC_COGNITO_USER_POOL_ID;
  const userPoolWebClientId = process.env.NEXT_PUBLIC_COGNITO_USER_POOL_CLIENT_ID;

  if (!region || !userPoolId || !userPoolWebClientId) {
    // Leave unconfigured in dev if not provided
    configured = true;
    return;
  }

  Amplify.configure({
    Auth: {
      region,
      userPoolId,
      userPoolWebClientId,
      mandatorySignIn: false,
    },
    ssr: true,
  } as any);
  configured = true;
}


