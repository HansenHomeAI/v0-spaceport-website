export const runtime = 'edge';

export async function GET(request: Request): Promise<Response> {
  try {
    const authHeader =
      request.headers.get('authorization') || request.headers.get('Authorization') || '';

    const env = {
      NEXT_PUBLIC_COGNITO_REGION: process.env.NEXT_PUBLIC_COGNITO_REGION || '',
      NEXT_PUBLIC_COGNITO_USER_POOL_ID: process.env.NEXT_PUBLIC_COGNITO_USER_POOL_ID || '',
      NEXT_PUBLIC_COGNITO_USER_POOL_CLIENT_ID:
        process.env.NEXT_PUBLIC_COGNITO_USER_POOL_CLIENT_ID || '',
      NEXT_PUBLIC_SUBSCRIPTION_API_URL: process.env.NEXT_PUBLIC_SUBSCRIPTION_API_URL || '',
    };

    const result: any = { env, hasAuthHeader: Boolean(authHeader) };

    if (authHeader.startsWith('Bearer ')) {
      const token = authHeader.slice('Bearer '.length);
      const parts = token.split('.');
      if (parts.length === 3) {
        try {
          const b64 = (s: string) => {
            const pad = s.length % 4;
            if (pad) s = s + '='.repeat(4 - pad);
            return atob(s.replace(/-/g, '+').replace(/_/g, '/'));
          };
          const payload = JSON.parse(b64(parts[1]));
          result.jwt = {
            iss: payload.iss,
            aud: payload.aud,
            sub: payload.sub,
            exp: payload.exp,
          };
        } catch (e) {
          result.jwtError = 'Failed to decode JWT payload';
        }
      }
    }

    return new Response(JSON.stringify(result), {
      status: 200,
      headers: { 'content-type': 'application/json; charset=utf-8' },
    });
  } catch (e) {
    return new Response(JSON.stringify({ error: 'debug failed' }), { status: 500 });
  }
}


