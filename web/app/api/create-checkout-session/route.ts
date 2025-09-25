import { resolveSubscriptionApiUrl } from 'lib/subscriptionApi';

export const runtime = 'edge';

export async function POST(request: Request): Promise<Response> {
  try {
    const target = resolveSubscriptionApiUrl('/create-checkout-session');

    if (target.kind === 'error') {
      return new Response(
        JSON.stringify({ error: target.error }),
        { 
          status: 500,
          headers: { 'content-type': 'application/json; charset=utf-8' }
        }
      );
    }

    const authorization =
      request.headers.get('authorization') || request.headers.get('Authorization') || '';

    if (!authorization) {
      return new Response(
        JSON.stringify({ error: 'Missing authorization token' }),
        {
          status: 401,
          headers: { 'content-type': 'application/json; charset=utf-8' }
        }
      );
    }

    const body = await request.json();

    const response = await fetch(target.url, {
      method: 'POST',
      headers: {
        Authorization: authorization,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    const raw = await response.text();
    let payload = raw;

    if (!raw) {
      payload = '{}';
    } else {
      try {
        // Validate JSON to avoid double encoding downstream
        JSON.parse(raw);
      } catch (parseError) {
        console.error('Failed to parse checkout session response', parseError);
        payload = JSON.stringify({ error: 'Invalid response from subscription service' });
      }
    }

    return new Response(payload, {
      status: response.status,
      headers: {
        'content-type': 'application/json; charset=utf-8',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
      }
    });

  } catch (error) {
    console.error('Error proxying checkout session request:', error);
    return new Response(
      JSON.stringify({ error: 'Failed to create checkout session' }),
      { 
        status: 500,
        headers: { 'content-type': 'application/json; charset=utf-8' }
      }
    );
  }
}

export async function OPTIONS(): Promise<Response> {
  return new Response(null, {
    status: 200,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    },
  });
}
